using System.Windows;
using System.Windows.Input;
using CapriPet.ViewModels;

namespace CapriPet;

public partial class MainWindow : Window
{
    private bool _isInitialLoaded;

    public MainWindow()
    {
        InitializeComponent();

        if (DataContext is MainViewModel vm)
        {
            vm.RequestClose += Close;
        }
    }

    private void Window_Loaded(object sender, RoutedEventArgs e)
    {
        // Исходное позиционирование в правом нижнем углу над панелью задач
        var workingArea = SystemParameters.WorkArea;
        Left = workingArea.Right - ActualWidth - 30;
        Top = workingArea.Bottom - ActualHeight - 30;
        _isInitialLoaded = true;
    }

    private void Window_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        if (!_isInitialLoaded || !e.PreviousSize.Width.Equals(0))
        {
            // Корректируем координаты: при росте размера окно расширяется вверх и влево от опоры
            double deltaWidth = e.NewSize.Width - e.PreviousSize.Width;
            double deltaHeight = e.NewSize.Height - e.PreviousSize.Height;

            Left -= deltaWidth / 2.0;
            Top -= deltaHeight;

            // Защита от выхода за границы экрана (WorkArea)
            ClampToScreenBounds();
        }
    }

    private void ClampToScreenBounds()
    {
        var workArea = SystemParameters.WorkArea;

        if (Left + ActualWidth > workArea.Right)
        {
            Left = workArea.Right - ActualWidth;
        }

        if (Left < workArea.Left)
        {
            Left = workArea.Left;
        }

        if (Top + ActualHeight > workArea.Bottom)
        {
            Top = workArea.Bottom - ActualHeight;
        }

        if (Top < workArea.Top)
        {
            Top = workArea.Top;
        }
    }

    private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ChangedButton == MouseButton.Left)
        {
            DragMove();
        }
    }

    private void Window_MouseRightButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (DataContext is MainViewModel vm)
        {
            vm.OpenSettingsCommand.Execute(null);
        }
    }
}
