using System.Windows;
using System.Windows.Input;
using CapriPet.ViewModels;

namespace CapriPet;

public partial class MainWindow : Window
{
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
        Left = workingArea.Right - Width - 30;
        Top = workingArea.Bottom - Height - 30;
    }

    private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ChangedButton == MouseButton.Left)
        {
            DragMove();
        }
    }
}
