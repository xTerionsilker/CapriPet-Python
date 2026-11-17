namespace CapriPet.Models;

public record DialoguePhrase(string Text, PetMood RequiredMood = PetMood.Idle);
