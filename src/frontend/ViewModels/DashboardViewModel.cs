// ViewModel for Dashboard module
using CommunityToolkit.Mvvm.ComponentModel;

namespace AgentOS.Desktop.ViewModels;

public partial class DashboardViewModel : ViewModelBase
{
    [ObservableProperty]
    private string _title = "Dashboard";
}
