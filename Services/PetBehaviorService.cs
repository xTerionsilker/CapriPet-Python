using System;
using System.Timers;
using CapriPet.Models;

namespace CapriPet.Services;

public class PetBehaviorService : IPetBehaviorService, IDisposable
{
    private PetState _state = new();
    private readonly Random _random = new();
    private readonly System.Timers.Timer _poseTimer;

    // Спрайты для базового состояния и сидения (lay отложен на будущее по запросу)
    private static readonly string[] AvailableSprites =
    [
        "pack://application:,,,/Assets/Sprites/base.png",
        "pack://application:,,,/Assets/Sprites/sit.png",
        "pack://application:,,,/Assets/Sprites/sit2.png",
        "pack://application:,,,/Assets/Sprites/sit3.png"
    ];

    public PetBehaviorService()
    {
        // Случайная смена позы каждые 4-8 секунд в режиме ожидания
        _poseTimer = new System.Timers.Timer(GetRandomInterval());
        _poseTimer.Elapsed += OnPoseTimerElapsed;
        _poseTimer.AutoReset = false;
        _poseTimer.Start();
    }

    public PetState CurrentState => _state;

    public event EventHandler<PetState>? StateChanged;

    private double GetRandomInterval() => _random.Next(4000, 8000);

    private void OnPoseTimerElapsed(object? sender, ElapsedEventArgs e)
    {
        RandomizePose();
        _poseTimer.Interval = GetRandomInterval();
        _poseTimer.Start();
    }

    public void RandomizePose()
    {
        // Выбираем следующий случайный спрайт, отличный от текущего
        string nextSprite;
        do
        {
            nextSprite = AvailableSprites[_random.Next(AvailableSprites.Length)];
        }
        while (AvailableSprites.Length > 1 && nextSprite == _state.SpritePath);

        _state = _state with
        {
            SpritePath = nextSprite
        };

        StateChanged?.Invoke(this, _state);
    }

    public void Interact()
    {
        RandomizePose();
        _poseTimer.Stop();
        _poseTimer.Interval = GetRandomInterval();
        _poseTimer.Start();
    }

    public string GetRandomPhrase() => string.Empty;

    public void Dispose()
    {
        _poseTimer.Stop();
        _poseTimer.Dispose();
        GC.SuppressFinalize(this);
    }
}
