using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace CapriPet.Services;

public class SpotifyControlService : ISpotifyControlService
{
    private const byte VK_MEDIA_NEXT_TRACK = 0xB0;
    private const byte VK_MEDIA_PREV_TRACK = 0xB1;
    private const byte VK_MEDIA_STOP = 0xB2;
    private const byte VK_MEDIA_PLAY_PAUSE = 0xB3;
    private const uint KEYEVENTF_KEYUP = 0x0002;

    [DllImport("user32.dll", SetLastError = true)]
    private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

    public bool IsSpotifyRunning
    {
        get
        {
            try
            {
                var processes = Process.GetProcessesByName("spotify");
                return processes.Length > 0;
            }
            catch
            {
                return false;
            }
        }
    }

    public string? CurrentTrackTitle
    {
        get
        {
            try
            {
                var processes = Process.GetProcessesByName("spotify");
                foreach (var process in processes)
                {
                    try
                    {
                        string title = process.MainWindowTitle;
                        if (!string.IsNullOrWhiteSpace(title) &&
                            !title.Equals("Spotify", StringComparison.OrdinalIgnoreCase) &&
                            !title.Equals("Spotify Free", StringComparison.OrdinalIgnoreCase) &&
                            !title.Equals("Spotify Premium", StringComparison.OrdinalIgnoreCase))
                        {
                            return title;
                        }
                    }
                    catch
                    {
                        // Some child processes may reject MainWindowTitle access
                    }
                }
            }
            catch
            {
                // Ignore process enumeration errors
            }

            return null;
        }
    }

    public void Play()
    {
        if (!IsSpotifyRunning)
        {
            LaunchSpotify();
            return;
        }

        // Если трек уже играет, ничего не делаем. Иначе шлем команду воспроизведения.
        if (CurrentTrackTitle == null)
        {
            SendMediaKey(VK_MEDIA_PLAY_PAUSE);
        }
    }

    public void Pause()
    {
        if (!IsSpotifyRunning)
        {
            return;
        }

        // Если играет трек, шлем паузу. Если уже на паузе, не трогаем.
        if (CurrentTrackTitle != null)
        {
            SendMediaKey(VK_MEDIA_PLAY_PAUSE);
        }
        else
        {
            // На всякий случай можно отправить STOP или PLAY_PAUSE
            SendMediaKey(VK_MEDIA_STOP);
        }
    }

    public void PlayPause()
    {
        if (!IsSpotifyRunning)
        {
            LaunchSpotify();
            return;
        }

        SendMediaKey(VK_MEDIA_PLAY_PAUSE);
    }

    public void NextTrack()
    {
        SendMediaKey(VK_MEDIA_NEXT_TRACK);
    }

    public void PreviousTrack()
    {
        SendMediaKey(VK_MEDIA_PREV_TRACK);
    }

    public bool Search(string query)
    {
        if (string.IsNullOrWhiteSpace(query))
        {
            return false;
        }

        string escapedQuery = Uri.EscapeDataString(query.Trim());

        try
        {
            // Попытка запуска через протокол spotify:search:
            Process.Start(new ProcessStartInfo
            {
                FileName = $"spotify:search:{escapedQuery}",
                UseShellExecute = true
            });
            return true;
        }
        catch
        {
            try
            {
                // Fallback на веб-версию в браузере, если приложение Spotify не установлено
                Process.Start(new ProcessStartInfo
                {
                    FileName = $"https://open.spotify.com/search/{escapedQuery}",
                    UseShellExecute = true
                });
                return true;
            }
            catch
            {
                return false;
            }
        }
    }

    private void LaunchSpotify()
    {
        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = "spotify:",
                UseShellExecute = true
            });
        }
        catch
        {
            // Fallback: запустить стандартный медиа-ключ
            SendMediaKey(VK_MEDIA_PLAY_PAUSE);
        }
    }

    private static void SendMediaKey(byte key)
    {
        keybd_event(key, 0, 0, UIntPtr.Zero);
        keybd_event(key, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
    }
}
