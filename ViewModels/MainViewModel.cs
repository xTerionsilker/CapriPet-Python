using System;
using System.Threading.Tasks;
using System.Windows.Input;
using CapriPet.Commands;
using CapriPet.Models;
using CapriPet.Services;

namespace CapriPet.ViewModels;

public class MainViewModel : BaseViewModel
{
    private readonly IPetBehaviorService _petService;
    private readonly IVoiceRecognitionService _voiceService;

    private string _speechText = "Привет! Я слушаю твой микрофон 🎙️";
    private string _petMoodText = "⚡ READY";
    private string _petFace = "( ^ ◕ ᴥ ◕ ^ )";
    private string _micStatusText = "Инициализация...";
    private bool _isMicActive;

    // Обязательный конструктор без параметров для XAML-парсера
    public MainViewModel() : this(null, null)
    {
    }

    public MainViewModel(
        IPetBehaviorService? petService,
        IVoiceRecognitionService? voiceService)
    {
        _petService = petService ?? new PetBehaviorService();
        _petService.StateChanged += OnPetStateChanged;

        _voiceService = voiceService ?? new VoiceRecognitionService();
        _voiceService.SpeechRecognized += OnSpeechRecognized;
        _voiceService.StatusChanged += OnVoiceStatusChanged;

        InteractCommand = new RelayCommand(OnInteract);
        CloseCommand = new RelayCommand(OnClose);
        ToggleMicCommand = new RelayCommand(async () => await ToggleMicAsync());
    }

    public string SpeechText
    {
        get => _speechText;
        set => SetProperty(ref _speechText, value);
    }

    public string PetMoodText
    {
        get => _petMoodText;
        set => SetProperty(ref _petMoodText, value);
    }

    public string PetFace
    {
        get => _petFace;
        set => SetProperty(ref _petFace, value);
    }

    public string MicStatusText
    {
        get => _micStatusText;
        set => SetProperty(ref _micStatusText, value);
    }

    public bool IsMicActive
    {
        get => _isMicActive;
        set
        {
            if (SetProperty(ref _isMicActive, value))
            {
                OnPropertyChanged(nameof(MicButtonIcon));
            }
        }
    }

    public string MicButtonIcon => IsMicActive ? "🎙️" : "🔇";

    public ICommand InteractCommand { get; }
    public ICommand CloseCommand { get; }
    public ICommand ToggleMicCommand { get; }

    public event Action? RequestClose;

    public async Task InitializeAsync()
    {
        await ToggleMicAsync();
    }

    private async Task ToggleMicAsync()
    {
        try
        {
            if (_voiceService.IsListening)
            {
                await _voiceService.StopAsync();
                IsMicActive = false;
            }
            else
            {
                IsMicActive = true;
                await _voiceService.StartAsync();
            }
        }
        catch (Exception ex)
        {
            MicStatusText = $"Ошибка: {ex.Message}";
            IsMicActive = false;
        }
    }

    private void OnSpeechRecognized(object? sender, string text)
    {
        // Выполняем обновление на UI потоке
        System.Windows.Application.Current?.Dispatcher?.Invoke(() =>
        {
            _petService.Interact();
            SpeechText = $"Ты сказал: «{text}» 🐾";
        });
    }

    private void OnVoiceStatusChanged(object? sender, string status)
    {
        System.Windows.Application.Current?.Dispatcher?.Invoke(() =>
        {
            MicStatusText = status;
        });
    }

    private void OnInteract()
    {
        _petService.Interact();
        var phrase = _petService.GetRandomPhrase();
        SpeechText = $"{phrase} (кликов: {_petService.CurrentState.InteractionCount})";
    }

    private void OnPetStateChanged(object? sender, PetState state)
    {
        (PetFace, PetMoodText) = state.Mood switch
        {
            PetMood.Happy => ("( ★ ◕ ᴥ ◕ ★ )", "💖 HAPPY"),
            PetMood.Playful => ("( ✧ ∇ ✧ )", "✨ PLAYFUL"),
            PetMood.Sleepy => ("( - ﹏ - )zzZ", "💤 SLEEPY"),
            _ => ("( ^ ◕ ᴥ ◕ ^ )", "⚡ IDLE")
        };
    }

    private void OnClose()
    {
        _ = _voiceService.DisposeAsync();
        RequestClose?.Invoke();
    }
}
