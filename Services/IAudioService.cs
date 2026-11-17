namespace CapriPet.Services;

public interface IAudioService
{
    void PlaySfx(string soundName);
    void PlayVoice(string speechText);
}
