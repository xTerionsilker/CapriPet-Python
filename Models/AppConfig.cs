namespace CapriPet.Models;

public class AppConfig
{
    public int ScaleStep { get; set; } = (int)PetScalePreset.Default;
    public double? WindowLeft { get; set; }
    public double? WindowTop { get; set; }
}
