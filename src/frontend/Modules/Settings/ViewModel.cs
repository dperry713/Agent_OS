using ReactiveUI;
using AgentOS.Frontend.Services;
using System.Reactive;
using System.Reactive.Linq;

namespace AgentOS.Frontend.Modules.Settings
{
    public class ViewModel : ReactiveObject
    {
        private readonly NavigationService _navigationService;
        private readonly SettingsService _settingsService;

        public ViewModel(NavigationService navigationService, SettingsService settingsService)
        {
            _navigationService = navigationService;
            _settingsService = settingsService;

            // Load persisted setting
            IsDarkTheme = _settingsService.GetDarkThemeEnabled();

            SaveCommand = ReactiveCommand.Create(SaveSettings);
        }

        private bool _isDarkTheme;
        public bool IsDarkTheme
        {
            get => _isDarkTheme;
            set => this.RaiseAndSetIfChanged(ref _isDarkTheme, value);
        }

        public ReactiveCommand<Unit, Unit> SaveCommand { get; }

        private void SaveSettings()
        {
            _settingsService.SetDarkThemeEnabled(IsDarkTheme);
            // Notify ThemeManager to apply change
            ThemeManager.ApplyTheme(IsDarkTheme ? "Dark" : "Light");
        }
    }
}
