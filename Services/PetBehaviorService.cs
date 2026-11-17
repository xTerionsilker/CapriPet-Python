using System;
using System.Timers;
using CapriPet.Models;

namespace CapriPet.Services;

public class PetBehaviorService : IPetBehaviorService, IDisposable
{
    private PetState _state = new();
    private readonly Random _random = new();
    private readonly System.Timers.Timer _poseTimer;
    private readonly ISpotifyControlService _spotifyService;

    private static readonly string[] AvailableSprites =
    [
        "pack://application:,,,/Assets/Sprites/base.png",
        "pack://application:,,,/Assets/Sprites/sit.png",
        "pack://application:,,,/Assets/Sprites/sit2.png",
        "pack://application:,,,/Assets/Sprites/sit3.png"
    ];

    private readonly string[] _randomResponses =
    [
        "Пакет данных принят. Нейросеть Capri на связи! ⚡",
        "Мяу! Фиксирую входящий запрос в логах ядра. 📡",
        "Слышу тебя четко. Телеметрия стабильна! 🐾",
        "Команда обработана процессором. Жду указаний! 🚀",
        "Сигнал расшифрован без ошибок. Я рядом! ✨"
    ];

    public PetBehaviorService(ISpotifyControlService? spotifyService = null)
    {
        _spotifyService = spotifyService ?? new SpotifyControlService();

        _poseTimer = new System.Timers.Timer(GetRandomInterval());
        _poseTimer.Elapsed += OnPoseTimerElapsed;
        _poseTimer.AutoReset = false;
        _poseTimer.Start();
    }

    public PetState CurrentState => _state;

    public event EventHandler<PetState>? StateChanged;

    private double GetRandomInterval() => _random.Next(5000, 10000);

    private void OnPoseTimerElapsed(object? sender, ElapsedEventArgs e)
    {
        RandomizePose();
        _poseTimer.Interval = GetRandomInterval();
        _poseTimer.Start();
    }

    public void RandomizePose()
    {
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

    public void SetPose(string spriteName)
    {
        string target = spriteName.ToLowerInvariant();
        string selected = AvailableSprites[0];

        foreach (var sprite in AvailableSprites)
        {
            if (sprite.ToLowerInvariant().Contains(target))
            {
                selected = sprite;
                break;
            }
        }

        _state = _state with
        {
            SpritePath = selected
        };

        StateChanged?.Invoke(this, _state);

        _poseTimer.Stop();
        _poseTimer.Interval = GetRandomInterval();
        _poseTimer.Start();
    }

    public string RespondToCommand(string command)
    {
        if (string.IsNullOrWhiteSpace(command))
        {
            return "Слушаю тебя! Напиши или скажи команду. 🐾";
        }

        string rawTrimmed = command.Trim();
        string clean = rawTrimmed.ToLowerInvariant();

        // 1. Поиск трека в Spotify (проверяем перед общими ключевыми словами)
        string[] searchPrefixes =
        [
            "найди трек",
            "найди песню",
            "поставь трек",
            "поставь песню",
            "включи трек",
            "включи песню",
            "search track",
            "найди",
            "search"
        ];

        foreach (var prefix in searchPrefixes)
        {
            if (clean.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                string query = rawTrimmed.Substring(prefix.Length).Trim(' ', ':', '"', '«', '»', '—', '-');
                if (string.IsNullOrWhiteSpace(query))
                {
                    return "Какой трек найти? Укажи название, например: «найди трек Daft Punk - Get Lucky». 🎵";
                }

                bool launched = _spotifyService.Search(query);
                if (launched)
                {
                    SetPose("sit");
                    return $"Ищу трек «{query}» в Spotify... 🎧";
                }
                else
                {
                    return $"Не удалось запустить поиск трека «{query}». ❌";
                }
            }
        }

        // 2. Управление воспроизведением Spotify: следующий трек
        if (clean.Contains("следующий") || clean.Contains("следующая") || clean.Contains("дальше") ||
            clean.Contains("вперед") || clean.Contains("скип") || clean.Contains("скипни") || clean == "next")
        {
            _spotifyService.NextTrack();
            SetPose("base");
            return "Переключаю на следующий трек! ⏭️";
        }

        // 3. Управление воспроизведением Spotify: предыдущий трек
        if (clean.Contains("предыдущий") || clean.Contains("предыдущая") || clean.Contains("назад") ||
            clean.Contains("prev") || clean == "back")
        {
            _spotifyService.PreviousTrack();
            SetPose("base");
            return "Возвращаю предыдущий трек. ⏮️";
        }

        // 4. Пауза / Стоп
        if (clean.Contains("пауза") || clean.Contains("стоп") || clean.Contains("останови") ||
            clean.Contains("выключи музыку") || clean.Contains("заглуши") || clean == "pause" || clean == "stop")
        {
            _spotifyService.Pause();
            SetPose("sit");
            return "Музыка в Spotify поставлена на паузу. ⏸️";
        }

        // 5. Воспроизведение / Играй
        if (clean.Contains("играй") || clean.Contains("плей") || clean.Contains("вруби") ||
            clean.Contains("включи музыку") || clean.Contains("продолжи") || clean.Contains("возобнови") || clean == "play")
        {
            _spotifyService.Play();
            SetPose("base");
            string? current = _spotifyService.CurrentTrackTitle;
            if (!string.IsNullOrWhiteSpace(current))
            {
                return $"Включаю! Играет: «{current}» 🎶";
            }
            return "Включаю воспроизведение в Spotify! 🎶";
        }

        // 6. Запрос текущего трека
        if (clean.Contains("что играет") || clean.Contains("какой трек") || clean.Contains("текущий трек"))
        {
            string? current = _spotifyService.CurrentTrackTitle;
            if (!string.IsNullOrWhiteSpace(current))
            {
                return $"Сейчас играет: «{current}» 🎧";
            }
            return "Сейчас ничего не играет или Spotify не запущен. 🔇";
        }

        // 7. Базовые интерактивные команды Capri
        if (clean.Contains("привет") || clean.Contains("хай") || clean.Contains("hello"))
        {
            SetPose("base");
            return "Привет, netrunner! Системы Capri активны. ⚡";
        }

        if (clean.Contains("сидеть") || clean.Contains("сядь") || clean.Contains("sit"))
        {
            SetPose("sit");
            return "Принято. Перехожу в режим ожидания (SIT). 🧘";
        }

        if (clean.Contains("встать") || clean.Contains("стой") || clean.Contains("base"))
        {
            SetPose("base");
            return "Встала в базовую стойку. Готова действовать! 🚀";
        }

        if (clean.Contains("статус") || clean.Contains("status") || clean.Contains("как дела"))
        {
            return "Телеметрия в норме. Ядро Capri функционирует на 100%! ⚡";
        }

        if (clean.Contains("кто ты") || clean.Contains("капри") || clean.Contains("capri"))
        {
            return "Я Capri — твой автономный кибер-питомец на C# WPF! 🎮";
        }

        if (clean.Contains("помощь") || clean.Contains("help") || clean.Contains("команды"))
        {
            return "Команды: статус, сидеть, встать, играй, пауза, следующий, предыдущий, найди трек <название>, что играет, кто ты.";
        }

        // 8. Случайный осмысленный кибер-ответ на любую произвольную фразу
        RandomizePose();
        string phrase = _randomResponses[_random.Next(_randomResponses.Length)];
        return $"«{rawTrimmed}» — {phrase}";
    }

    public void Interact()
    {
        RandomizePose();
        _poseTimer.Stop();
        _poseTimer.Interval = GetRandomInterval();
        _poseTimer.Start();
    }

    public string GetRandomPhrase()
    {
        return _randomResponses[_random.Next(_randomResponses.Length)];
    }

    public void Dispose()
    {
        _poseTimer.Stop();
        _poseTimer.Dispose();
        GC.SuppressFinalize(this);
    }
}
