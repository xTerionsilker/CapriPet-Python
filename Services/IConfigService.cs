using System;
using CapriPet.Models;

namespace CapriPet.Services;

public interface IConfigService
{
    AppConfig Current { get; }
    void Load();
    void Save();
    void Update(Action<AppConfig> updateAction);
}
