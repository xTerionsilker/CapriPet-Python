namespace CapriPet.Models;

public enum PetScalePreset
{
    Tiny = 0,
    Small = 1,
    Medium = 2,
    Default = 3,
    Big = 4,
    VeryBig = 5,
    Hardcore = 6
}

public static class PetScaleExtensions
{
    public static double ToPixelSize(this PetScalePreset preset) => preset switch
    {
        PetScalePreset.Tiny => 100.0,
        PetScalePreset.Small => 140.0,
        PetScalePreset.Medium => 180.0,
        PetScalePreset.Default => 220.0,
        PetScalePreset.Big => 280.0,
        PetScalePreset.VeryBig => 360.0,
        PetScalePreset.Hardcore => 460.0,
        _ => 220.0
    };

    public static string ToDisplayName(this PetScalePreset preset) => preset switch
    {
        PetScalePreset.Tiny => "TINY",
        PetScalePreset.Small => "SMALL",
        PetScalePreset.Medium => "MEDIUM",
        PetScalePreset.Default => "DEFAULT",
        PetScalePreset.Big => "BIG",
        PetScalePreset.VeryBig => "VERY BIG",
        PetScalePreset.Hardcore => "HARDCORE",
        _ => "DEFAULT"
    };
}
