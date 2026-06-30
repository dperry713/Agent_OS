// ViewModel for Projects module
using CommunityToolkit.Mvvm.ComponentModel;

namespace AgentOS.Desktop.ViewModels;

public partial class ProjectsViewModel : ViewModelBase
{
    [ObservableProperty]
    private string _title = "Projects";
}
