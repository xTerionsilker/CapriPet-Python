using System;
using CapriPet.Models;

namespace CapriPet.Services;

public interface IPetBehaviorService
{
    PetState CurrentState { get; }
    event EventHandler<PetState>? StateChanged;

    void Interact();
    string RespondToCommand(string command);
    string GetRandomPhrase();
    void SetPose(string spriteName);
}
