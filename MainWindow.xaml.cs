using System;
using System.Windows;
using System.Windows.Input;

namespace CapriPet;

public partial class MainWindow : Window
{
    private int _clickCount = 0;
    private readonly string[] _phrases =
    [
        "Мяу! Я теперь на C# и WPF! ⚡",
        "Тяни меня куда угодно за окно! 🚀",
        "В .NET скорость просто запредельная! 🔥",
        "Анимации и эффекты работают через DirectX! 🎮",
        "Готов к добавлению новых команд и звуков! 🎶"
    ];

    public MainWindow()
    {
        InitializeComponent();
    }

    private void Window_Loaded(object sender, RoutedEventArgs e)
    {
        // Размещаем питомца в правом нижнем углу экрана над панелью задач
        var workingArea = SystemParameters.WorkArea;
        Left = workingArea.Right - Width - 30;
        Top = workingArea.Bottom - Height - 30;
    }

    private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        // Позволяет перетаскивать окно удерживанием левой кнопки мыши
        if (e.ChangedButton == MouseButton.Left)
        {
            DragMove();
        }
    }

    private void PetButton_Click(object sender, RoutedEventArgs e)
    {
        _clickCount++;
        string phrase = _phrases[_clickCount % _phrases.Length];
        SpeechText.Text = $"{phrase} (кликов: {_clickCount})";
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e)
    {
        Close();
    }
}
