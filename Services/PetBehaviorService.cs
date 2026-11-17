using System;
using CapriPet.Models;

namespace CapriPet.Services;

public class PetBehaviorService : IPetBehaviorService
{
    private PetState _state = new();
    private readonly Random _random = new();

    private readonly string[] _phrases =
    [
        "Мяу! Я теперь на чистой архитектуре C# ⚡",
        "Тяни меня куда угодно за окно! 🐾",
        "MVVM разделяет интерфейс и логику на 100%! 🔥",
        "Анимации и эффекты готовы к расширению! 🎮",
        "Готов к добавлению новых сервисов и звуков! 🎶"
    ];

    public PetState CurrentState => _state;

    public event EventHandler<PetState>? StateChanged;

    public void Interact()
    {
        var nextMood = (_state.InteractionCount % 3) switch
        {
            0 => PetMood.Happy,
            1 => PetMood.Playful,
            _ => PetMood.Idle
        };

        _state = _state with
        {
            InteractionCount = _state.InteractionCount + 1,
            Mood = nextMood
        };

        StateChanged?.Invoke(this, _state);
    }

    public string GetRandomPhrase()
    {
        return _phrases[_random.Next(_phrases.Length)];
    }
}
