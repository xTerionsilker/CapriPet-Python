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
    private string _currentSpriteSource = "pack://application:,,,/Assets/Sprites/base.png";

    private int _scaleStep = (int)PetScalePreset.Default;
    private double _petSize = PetScalePreset.Default.ToPixelSize();
    private string _scaleDisplayName = PetScalePreset.Default.ToDisplayName();
    private string _scalePixelText = $"({(int)PetScalePreset.Default.ToPixelSize()} x {(int)PetScalePreset.Default.ToPixelSize()} px)";

    private SettingsWindow? _settingsWindow;

    public MainViewModel() : this(null)
    {
    }

    public MainViewModel(IPetBehaviorService? petService)
    {
        _petService = petService ?? new PetBehaviorService();
        _petService.StateChanged += OnPetStateChanged;

        CloseCommand = new RelayCommand(OnClose);
        OpenSettingsCommand = new RelayCommand(OnOpenSettings);

        _currentSpriteSource = _petService.CurrentState.SpritePath;
    }

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
            if (SetProperty(ref _scaleStep, value))
            {
                var preset = (PetScalePreset)Math.Clamp(value, 0, 6);
                PetSize = preset.ToPixelSize();
                ScaleDisplayName = preset.ToDisplayName();
                ScalePixelText = $"({(int)PetSize} x {(int)PetSize} px)";
            }
        }
    }

    public double PetSize
    {
        get => _petSize;
        set
        {
            if (SetProperty(ref _petSize, value))
            {
                OnPropertyChanged(nameof(WindowSize));
            }
        }
    }

    public double WindowSize => PetSize + 24;

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
