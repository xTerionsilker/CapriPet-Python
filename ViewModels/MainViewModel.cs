using System;
using System.Windows.Input;
using CapriPet.Commands;
using CapriPet.Models;
using CapriPet.Services;
using CapriPet.Views;

namespace CapriPet.ViewModels;

public class MainViewModel : BaseViewModel
{
    private readonly IPetBehaviorService _petService;
    private readonly IConfigService _configService;

    private string _currentSpriteSource = "pack://application:,,,/Assets/Sprites/base.png";
    private int _scaleStep;
    private double _petSize;
    private string _scaleDisplayName = string.Empty;
    private string _scalePixelText = string.Empty;

    private SettingsWindow? _settingsWindow;

    public MainViewModel() : this(null, null)
    {
    }

    public MainViewModel(IPetBehaviorService? petService, IConfigService? configService = null)
    {
        _configService = configService ?? new ConfigService();
        _petService = petService ?? new PetBehaviorService();
        _petService.StateChanged += OnPetStateChanged;

        CloseCommand = new RelayCommand(OnClose);
        OpenSettingsCommand = new RelayCommand(OnOpenSettings);

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

    public ICommand CloseCommand { get; }
    public ICommand OpenSettingsCommand { get; }

    public event Action? RequestClose;

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

        RequestClose?.Invoke();
    }
}
