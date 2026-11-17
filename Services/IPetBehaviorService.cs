using System;
using CapriPet.Models;

namespace CapriPet.Services;

public interface IPetBehaviorService
{
    PetState CurrentState { get; }
    event EventHandler<PetState>? StateChanged;

    void Interact();
    string GetRandomPhrase();
}
