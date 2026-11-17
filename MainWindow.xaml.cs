using System;
using System.ComponentModel;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media.Animation;
using System.Windows.Threading;
using CapriPet.ViewModels;

namespace CapriPet;

public partial class MainWindow : Window
{
    private bool _isInitialLoaded;
    private Storyboard? _glitchInStoryboard;
    private Storyboard? _glitchOutStoryboard;
    private readonly DispatcherTimer _hideButtonsTimer;
    private bool _isControlPanelVisible;

    public MainWindow()
    {
        InitializeComponent();

        _hideButtonsTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(3)
        };
        _hideButtonsTimer.Tick += OnHideButtonsTimerTick;

        if (DataContext is MainViewModel vm)
        {
            vm.RequestClose += Close;
            vm.PropertyChanged += OnViewModelPropertyChanged;
        }
    }

    private void Window_Loaded(object sender, RoutedEventArgs e)
    {
        _glitchInStoryboard = TryFindResource("GlitchInStoryboard") as Storyboard;
        _glitchOutStoryboard = TryFindResource("GlitchOutStoryboard") as Storyboard;

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
        // Контекстное меню вызывается нативно через WPF ContextMenu
    }

    private void PetInteractiveArea_MouseEnter(object sender, MouseEventArgs e)
    {
        ShowControlPanel();
    }

    private void PetInteractiveArea_MouseLeave(object sender, MouseEventArgs e)
    {
        if (DataContext is MainViewModel vm && vm.IsTextInputOpen)
        {
            return;
        }

        _hideButtonsTimer.Stop();
        _hideButtonsTimer.Start();
    }

    private void OnHideButtonsTimerTick(object? sender, EventArgs e)
    {
        _hideButtonsTimer.Stop();

        if (PetInteractiveArea.IsMouseOver)
        {
            return;
        }

        if (DataContext is MainViewModel vm && vm.IsTextInputOpen)
        {
            return;
        }

        HideControlPanel();
    }

    private void ShowControlPanel()
    {
        _hideButtonsTimer.Stop();

        if (!_isControlPanelVisible)
        {
            _isControlPanelVisible = true;
            ControlPanel.IsHitTestVisible = true;
            _glitchOutStoryboard?.Stop(this);
            _glitchInStoryboard?.Begin(this);
        }
    }

    private void HideControlPanel()
    {
        if (_isControlPanelVisible)
        {
            _isControlPanelVisible = false;
            _glitchInStoryboard?.Stop(this);
            _glitchOutStoryboard?.Begin(this);
            ControlPanel.IsHitTestVisible = false;
        }
    }

    private void OnViewModelPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(MainViewModel.IsTextInputOpen))
        {
            if (DataContext is MainViewModel vm && !vm.IsTextInputOpen)
            {
                if (!PetInteractiveArea.IsMouseOver)
                {
                    _hideButtonsTimer.Stop();
                    _hideButtonsTimer.Start();
                }
            }
        }
    }

    protected override void OnClosing(CancelEventArgs e)
    {
        _hideButtonsTimer.Stop();

        if (DataContext is MainViewModel vm)
        {
            vm.PropertyChanged -= OnViewModelPropertyChanged;
        }

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
