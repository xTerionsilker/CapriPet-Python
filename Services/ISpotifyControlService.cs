using System;

namespace CapriPet.Services;

public interface ISpotifyControlService
{
    bool IsSpotifyRunning { get; }
    string? CurrentTrackTitle { get; }

    void Play();
    void Pause();
    void PlayPause();
    void NextTrack();
    void PreviousTrack();
    bool Search(string query);
}
