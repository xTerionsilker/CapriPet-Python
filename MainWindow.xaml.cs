using System;
using System.ComponentModel;
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
        var workingArea = SystemParameters.WorkArea;

        if (DataContext is MainViewModel vm && vm.SavedLeft.HasValue && vm.SavedTop.HasValue)
        {
            Left = vm.SavedLeft.Value;
            Top = vm.SavedTop.Value;
            ClampToScreenBounds();
        }
        else
        {
            Left = workingArea.Right - ActualWidth - 30;
            Top = workingArea.Bottom - ActualHeight - 30;
        }

        _isInitialLoaded = true;
        SaveCurrentPosition();
    }

    private void Window_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        if (_isInitialLoaded && !e.PreviousSize.Width.Equals(0))
        {
            // При изменении размера расширяемся вверх и влево от точки опоры
            double deltaWidth = e.NewSize.Width - e.PreviousSize.Width;
            double deltaHeight = e.NewSize.Height - e.PreviousSize.Height;

            Left -= deltaWidth / 2.0;
            Top -= deltaHeight;

            ClampToScreenBounds();
            SaveCurrentPosition();
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
            SaveCurrentPosition();
        }
    }

    private void Window_MouseRightButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (DataContext is MainViewModel vm)
        {
            vm.OpenSettingsCommand.Execute(null);
        }
    }

    protected override void OnClosing(CancelEventArgs e)
    {
        SaveCurrentPosition();
        base.OnClosing(e);
    }

    private void SaveCurrentPosition()
    {
        if (_isInitialLoaded && DataContext is MainViewModel vm)
        {
            vm.SaveWindowPosition(Left, Top);
        }
    }
}
