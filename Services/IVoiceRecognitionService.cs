using System;
using System.Threading.Tasks;

namespace CapriPet.Services;

public interface IVoiceRecognitionService : IAsyncDisposable
{
    bool IsListening { get; }
    string CurrentStatus { get; }

    event EventHandler<string>? SpeechRecognized;
    event EventHandler<string>? StatusChanged;

    Task StartAsync();
    Task StopAsync();
}
