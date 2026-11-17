using System;
using System.Windows.Input;
using CapriPet.Commands;
using CapriPet.Models;
using CapriPet.Services;

namespace CapriPet.ViewModels;

public class MainViewModel : BaseViewModel
{
    private readonly IPetBehaviorService _petService;
    private string _currentSpriteSource = "pack://application:,,,/Assets/Sprites/base.png";

    public MainViewModel() : this(null)
    {
    }

    public MainViewModel(IPetBehaviorService? petService)
    {
        _petService = petService ?? new PetBehaviorService();
        _petService.StateChanged += OnPetStateChanged;

        CloseCommand = new RelayCommand(OnClose);
        _currentSpriteSource = _petService.CurrentState.SpritePath;
    }

    public string CurrentSpriteSource
    {
        get => _currentSpriteSource;
        set => SetProperty(ref _currentSpriteSource, value);
    }

    public ICommand CloseCommand { get; }

    public event Action? RequestClose;

    private void OnPetStateChanged(object? sender, PetState state)
    {
        System.Windows.Application.Current?.Dispatcher?.Invoke(() =>
        {
            CurrentSpriteSource = state.SpritePath;
        });
    }

    private void OnClose()
    {
        if (_petService is IDisposable disposable)
        {
            disposable.Dispose();
        }

        RequestClose?.Invoke();
    }
}
