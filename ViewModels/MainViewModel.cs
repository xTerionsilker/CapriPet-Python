using System;
using System.Threading.Tasks;
using System.Windows.Input;
using System.Windows.Media;
using CapriPet.Commands;
using CapriPet.Models;
using CapriPet.Services;
using CapriPet.Views;

namespace CapriPet.ViewModels;

public class MainViewModel : BaseViewModel
{
    private readonly IPetBehaviorService _petService;
    private readonly IConfigService _configService;
    private readonly IVoiceRecognitionService _voiceService;

    private string _currentSpriteSource = "pack://application:,,,/Assets/Sprites/base.png";
    private int _scaleStep;
    private double _petSize;
    private string _scaleDisplayName = string.Empty;
    private string _scalePixelText = string.Empty;

    private bool _isMicActive;
    private bool _isTextInputOpen;
    private string _inputPromptText = string.Empty;

    private SettingsWindow? _settingsWindow;

    public MainViewModel() : this(null, null, null)
    {
    }

    public MainViewModel(
        IPetBehaviorService? petService,
        IConfigService? configService = null,
        IVoiceRecognitionService? voiceService = null)
    {
        _configService = configService ?? new ConfigService();
        _petService = petService ?? new PetBehaviorService();
        _petService.StateChanged += OnPetStateChanged;

        _voiceService = voiceService ?? new VoiceRecognitionService();
        _voiceService.SpeechRecognized += OnSpeechRecognized;

        CloseCommand = new RelayCommand(OnClose);
        OpenSettingsCommand = new RelayCommand(OnOpenSettings);
        ToggleMicCommand = new RelayCommand(async () => await ToggleMicAsync());
        ToggleTextInputCommand = new RelayCommand(OnToggleTextInput);
        SubmitTextCommand = new RelayCommand(OnSubmitText);

        _currentSpriteSource = _petService.CurrentState.SpritePath;

        // Загрузка масштаба из сохраненной конфигурации
        ApplyScalePreset(_configService.Current.ScaleStep, saveConfig: false);
    }

    public double? SavedLeft => _configService.Current.WindowLeft;
    public double? SavedTop => _configService.Current.WindowTop;

    public string CurrentSpriteSource
    {
        get => _currentSpriteSource;
        set => SetProperty(ref _currentSpriteSource, value);
    }

    public int ScaleStep
    {
        get => _scaleStep;
        set
        {
            if (_scaleStep != value)
            {
                ApplyScalePreset(value, saveConfig: true);
            }
        }
    }

    public double PetSize
    {
        get => _petSize;
        set => SetProperty(ref _petSize, value);
    }

    public string ScaleDisplayName
    {
        get => _scaleDisplayName;
        set => SetProperty(ref _scaleDisplayName, value);
    }

    public string ScalePixelText
    {
        get => _scalePixelText;
        set => SetProperty(ref _scalePixelText, value);
    }

    public bool IsMicActive
    {
        get => _isMicActive;
        set
        {
            if (SetProperty(ref _isMicActive, value))
            {
                OnPropertyChanged(nameof(MicIcon));
                OnPropertyChanged(nameof(MicColorBrush));
            }
        }
    }

    public string MicIcon => IsMicActive ? "🎙️" : "🔇";
    public Brush MicColorBrush => IsMicActive ? new SolidColorBrush(Color.FromRgb(0x0F, 0xFF, 0x55)) : new SolidColorBrush(Color.FromRgb(0xFE, 0x09, 0x29));

    public bool IsTextInputOpen
    {
        get => _isTextInputOpen;
        set => SetProperty(ref _isTextInputOpen, value);
    }

    public string InputPromptText
    {
        get => _inputPromptText;
        set => SetProperty(ref _inputPromptText, value);
    }

    public ICommand CloseCommand { get; }
    public ICommand OpenSettingsCommand { get; }
    public ICommand ToggleMicCommand { get; }
    public ICommand ToggleTextInputCommand { get; }
    public ICommand SubmitTextCommand { get; }

    public event Action? RequestClose;

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
        catch
        {
            IsMicActive = false;
        }
    }

    private void OnSpeechRecognized(object? sender, string text)
    {
        System.Windows.Application.Current?.Dispatcher?.Invoke(() =>
        {
            // Капри реагирует сменой позы на распознанную речь
            _petService.Interact();
        });
    }

    private void OnToggleTextInput()
    {
        IsTextInputOpen = !IsTextInputOpen;
    }

    private void OnSubmitText()
    {
        if (!string.IsNullOrWhiteSpace(InputPromptText))
        {
            // Капри реагирует на отправленный текст
            _petService.Interact();
            InputPromptText = string.Empty;
            IsTextInputOpen = false;
        }
    }

    private void ApplyScalePreset(int step, bool saveConfig)
    {
        int clampedStep = Math.Clamp(step, 0, 6);
        _scaleStep = clampedStep;
        OnPropertyChanged(nameof(ScaleStep));

        var preset = (PetScalePreset)clampedStep;
        PetSize = preset.ToPixelSize();
        ScaleDisplayName = preset.ToDisplayName();
        ScalePixelText = $"({(int)PetSize} x {(int)PetSize} px)";

        if (saveConfig)
        {
            _configService.Update(c => c.ScaleStep = clampedStep);
        }
    }

    public void SaveWindowPosition(double left, double top)
    {
        _configService.Update(c =>
        {
            c.WindowLeft = left;
            c.WindowTop = top;
        });
    }

    private void OnPetStateChanged(object? sender, PetState state)
    {
        System.Windows.Application.Current?.Dispatcher?.Invoke(() =>
        {
            CurrentSpriteSource = state.SpritePath;
        });
    }

    private void OnOpenSettings()
    {
        if (_settingsWindow != null && _settingsWindow.IsLoaded)
        {
            _settingsWindow.Activate();
            return;
        }

        _settingsWindow = new SettingsWindow
        {
            DataContext = this
        };
        _settingsWindow.Closed += (_, _) => _settingsWindow = null;
        _settingsWindow.Show();
    }

    private void OnClose()
    {
        _settingsWindow?.Close();

        if (_petService is IDisposable disposable)
        {
            disposable.Dispose();
        }

        _ = _voiceService.DisposeAsync();

        RequestClose?.Invoke();
    }
}
