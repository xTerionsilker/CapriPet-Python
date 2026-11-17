namespace CapriPet.Models;

public enum PetMood
{
    Idle,
    Happy,
    Playful,
    Sleepy,
    Alert
}

public record PetState
{
    public PetMood Mood { get; init; } = PetMood.Idle;
    public string SpritePath { get; init; } = "pack://application:,,,/Assets/Sprites/base.png";
    public double Energy { get; init; } = 100.0;
    public int InteractionCount { get; init; } = 0;
}
