// ViewModel for UserProfiles module
using CommunityToolkit.Mvvm.ComponentModel;

namespace AgentOS.Desktop.ViewModels;

public partial class UserProfilesViewModel : ViewModelBase
{
    [ObservableProperty]
    private string _title = "User Profiles";
}
