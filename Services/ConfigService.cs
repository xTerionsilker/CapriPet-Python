using System;
using System.IO;
using System.Text.Json;
using CapriPet.Models;

namespace CapriPet.Services;

public class ConfigService : IConfigService
{
    private readonly string _configPath;
    private AppConfig _current = new();
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true
    };

    public ConfigService(string? customPath = null)
    {
        if (!string.IsNullOrWhiteSpace(customPath))
        {
            _configPath = customPath;
        }
        else
        {
            var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            _configPath = Path.Combine(appData, "CapriPet", "config.json");
        }

        Load();
    }

    public AppConfig Current => _current;

    public void Load()
    {
        try
        {
            if (File.Exists(_configPath))
            {
                string json = File.ReadAllText(_configPath);
                var loaded = JsonSerializer.Deserialize<AppConfig>(json, JsonOptions);
                if (loaded != null)
                {
                    _current = loaded;
                    return;
                }
            }
        }
        catch
        {
            // При повреждении файла настроек откатываемся на значения по умолчанию
        }

        _current = new AppConfig();
    }

    public void Save()
    {
        try
        {
            var dir = Path.GetDirectoryName(_configPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            string json = JsonSerializer.Serialize(_current, JsonOptions);
            string tmpPath = _configPath + ".tmp";

            File.WriteAllText(tmpPath, json);
            File.Move(tmpPath, _configPath, overwrite: true);
        }
        catch
        {
            // Ошибки записи конфигурации не должны приводить к падению приложения
        }
    }

    public void Update(Action<AppConfig> updateAction)
    {
        updateAction(_current);
        Save();
    }
}
