using System;
using System.IO;
using System.Text;
using System.Threading.Channels;
using System.Threading.Tasks;
using NAudio.Wave;
using Whisper.net;
using Whisper.net.Ggml;

namespace CapriPet.Services;

public class VoiceRecognitionService : IVoiceRecognitionService
{
    private readonly string _modelPath;
    private readonly WaveFormat _waveFormat = new(16000, 16, 1); // 16kHz, 16-bit, Mono

    private WaveIn? _waveIn;
    private WhisperFactory? _whisperFactory;
    private WhisperProcessor? _processor;

    private readonly MemoryStream _recordedAudioBuffer = new();
    private readonly object _audioLock = new();

    private bool _isSpeaking;
    private DateTime _lastSpeechTime = DateTime.MinValue;
    private DateTime _speechStartTime = DateTime.MinValue;

    private const double SilenceThreshold = 0.02; // Порог чувствительности микрофона (RMS)
    private readonly TimeSpan _silenceTimeout = TimeSpan.FromMilliseconds(800);
    private readonly TimeSpan _minSpeechDuration = TimeSpan.FromMilliseconds(450);
    private readonly TimeSpan _maxSpeechDuration = TimeSpan.FromSeconds(12);

    private readonly Channel<byte[]> _transcriptionQueue = Channel.CreateUnbounded<byte[]>();
    private Task? _transcriptionWorkerTask;
    private bool _isDisposed;

    public bool IsListening { get; private set; }
    public string CurrentStatus { get; private set; } = "Готов";

    public event EventHandler<string>? SpeechRecognized;
    public event EventHandler<string>? StatusChanged;

    public VoiceRecognitionService(string? modelPath = null)
    {
        _modelPath = modelPath ?? Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Assets", "Models", "ggml-base.bin");
    }

    private void SetStatus(string status)
    {
        CurrentStatus = status;
        StatusChanged?.Invoke(this, status);
    }

    public async Task StartAsync()
    {
        if (IsListening) return;

        try
        {
            if (WaveIn.DeviceCount == 0)
            {
                SetStatus("Микрофон не обнаружен в Windows ❌");
                return;
            }

            if (_processor == null)
            {
                await InitializeWhisperAsync();
            }

            _transcriptionWorkerTask ??= Task.Run(ProcessTranscriptionQueueAsync);

            _waveIn = new WaveIn
            {
                WaveFormat = _waveFormat,
                BufferMilliseconds = 50
            };

            _waveIn.DataAvailable += OnAudioDataAvailable;
            _waveIn.RecordingStopped += OnRecordingStopped;

            _waveIn.StartRecording();
            IsListening = true;
            SetStatus("Слушаю микрофон 🎙️");
        }
        catch (Exception ex)
        {
            SetStatus($"Ошибка аудио: {ex.Message}");
        }
    }

    public Task StopAsync()
    {
        if (!IsListening) return Task.CompletedTask;

        IsListening = false;
        try
        {
            _waveIn?.StopRecording();
            _waveIn?.Dispose();
            _waveIn = null;
        }
        catch
        {
            // Игнорируем ошибки при остановке
        }

        SetStatus("Микрофон выключен 🔇");
        return Task.CompletedTask;
    }

    private async Task InitializeWhisperAsync()
    {
        if (!File.Exists(_modelPath))
        {
            var fallbackPath = Path.Combine(Directory.GetCurrentDirectory(), "Assets", "Models", Path.GetFileName(_modelPath));
            if (File.Exists(fallbackPath))
            {
                var dir = Path.GetDirectoryName(_modelPath);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                File.Copy(fallbackPath, _modelPath, overwrite: true);
            }
            else
            {
                await DownloadModelSafelyAsync(_modelPath);
            }
        }

        SetStatus("Инициализация Whisper...");
        try
        {
            _whisperFactory = WhisperFactory.FromPath(_modelPath);
        }
        catch
        {
            SetStatus("Файл поврежден, повторная загрузка модели...");
            if (File.Exists(_modelPath)) File.Delete(_modelPath);
            await DownloadModelSafelyAsync(_modelPath);
            _whisperFactory = WhisperFactory.FromPath(_modelPath);
        }

        _processor = _whisperFactory.CreateBuilder()
            .WithLanguage("ru")
            .Build();
    }

    private async Task DownloadModelSafelyAsync(string targetPath)
    {
        SetStatus("Загрузка модели Whisper (русский язык)...");
        var dir = Path.GetDirectoryName(targetPath);
        if (!string.IsNullOrEmpty(dir))
        {
            Directory.CreateDirectory(dir);
        }

        string tempPath = targetPath + ".tmp";
        if (File.Exists(tempPath)) File.Delete(tempPath);

        await using (var modelStream = await WhisperGgmlDownloader.Default.GetGgmlModelAsync(GgmlType.Base))
        await using (var fileWriter = File.Create(tempPath))
        {
            await modelStream.CopyToAsync(fileWriter);
        }

        File.Move(tempPath, targetPath, overwrite: true);
    }

    private void OnAudioDataAvailable(object? sender, WaveInEventArgs e)
    {
        if (!IsListening) return;

        double rms = CalculateRms(e.Buffer, e.BytesRecorded);
        var now = DateTime.UtcNow;

        lock (_audioLock)
        {
            if (rms > SilenceThreshold)
            {
                if (!_isSpeaking)
                {
                    _isSpeaking = true;
                    _speechStartTime = now;
                    _recordedAudioBuffer.SetLength(0);
                    SetStatus("Слышу голос... 🗣️");
                }
                _lastSpeechTime = now;
                _recordedAudioBuffer.Write(e.Buffer, 0, e.BytesRecorded);
            }
            else if (_isSpeaking)
            {
                _recordedAudioBuffer.Write(e.Buffer, 0, e.BytesRecorded);

                bool silenceElapsed = (now - _lastSpeechTime) > _silenceTimeout;
                bool maxDurationReached = (now - _speechStartTime) > _maxSpeechDuration;

                if (silenceElapsed || maxDurationReached)
                {
                    _isSpeaking = false;
                    var speechDuration = now - _speechStartTime;

                    if (speechDuration >= _minSpeechDuration && _recordedAudioBuffer.Length > 0)
                    {
                        byte[] pcmData = _recordedAudioBuffer.ToArray();
                        _transcriptionQueue.Writer.TryWrite(pcmData);
                        SetStatus("Распознаю речь... ⚡");
                    }
                    else
                    {
                        SetStatus("Слушаю микрофон 🎙️");
                    }
                    _recordedAudioBuffer.SetLength(0);
                }
            }
        }
    }

    private async Task ProcessTranscriptionQueueAsync()
    {
        while (!_isDisposed && await _transcriptionQueue.Reader.WaitToReadAsync())
        {
            while (_transcriptionQueue.Reader.TryRead(out var pcmData))
            {
                if (_processor == null || pcmData.Length == 0) continue;

                try
                {
                    using var wavStream = new MemoryStream();
                    using (var writer = new WaveFileWriter(wavStream, _waveFormat))
                    {
                        writer.Write(pcmData, 0, pcmData.Length);
                    }
                    wavStream.Position = 0;

                    var sb = new StringBuilder();
                    await foreach (var result in _processor.ProcessAsync(wavStream))
                    {
                        sb.Append(result.Text);
                    }

                    string recognized = CleanRecognizedText(sb.ToString());
                    if (!string.IsNullOrWhiteSpace(recognized))
                    {
                        SpeechRecognized?.Invoke(this, recognized);
                    }
                }
                catch (Exception ex)
                {
                    SetStatus($"Ошибка распознавания: {ex.Message}");
                }
                finally
                {
                    if (IsListening)
                    {
                        SetStatus("Слушаю микрофон 🎙️");
                    }
                }
            }
        }
    }

    private static double CalculateRms(byte[] buffer, int bytesRecorded)
    {
        long sum = 0;
        int sampleCount = bytesRecorded / 2;
        if (sampleCount == 0) return 0;

        for (int i = 0; i < bytesRecorded; i += 2)
        {
            short sample = (short)(buffer[i] | (buffer[i + 1] << 8));
            sum += sample * sample;
        }

        double mean = sum / (double)sampleCount;
        return Math.Sqrt(mean) / 32768.0;
    }

    private static string CleanRecognizedText(string text)
    {
        return text.Trim().Trim('[', ']', '(', ')');
    }

    private void OnRecordingStopped(object? sender, StoppedEventArgs e)
    {
        if (e.Exception != null)
        {
            SetStatus($"Микрофон отключен: {e.Exception.Message}");
        }
    }

    public async ValueTask DisposeAsync()
    {
        if (_isDisposed) return;
        _isDisposed = true;

        await StopAsync();
        _transcriptionQueue.Writer.Complete();

        _processor?.Dispose();
        _whisperFactory?.Dispose();
        _recordedAudioBuffer.Dispose();
        GC.SuppressFinalize(this);
    }
}
