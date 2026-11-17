using System.Windows.Input;
using CapriPet.Commands;
using CapriPet.Models;
using CapriPet.Services;

namespace CapriPet.ViewModels;

public class MainViewModel : BaseViewModel
{
    private readonly IPetBehaviorService _petService;
    private string _speechText = "Привет! Перетаскивай меня мышкой 🐾";
    private string _petMoodText = "⚡ READY";
    private string _petFace = "( ^ ◕ ᴥ ◕ ^ )";

    public MainViewModel(IPetBehaviorService? petService = null)
    {
        _petService = petService ?? new PetBehaviorService();
        _petService.StateChanged += OnPetStateChanged;

        InteractCommand = new RelayCommand(OnInteract);
        CloseCommand = new RelayCommand(OnClose);
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

    public ICommand InteractCommand { get; }
    public ICommand CloseCommand { get; }

    public event Action? RequestClose;

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
        RequestClose?.Invoke();
    }
}
