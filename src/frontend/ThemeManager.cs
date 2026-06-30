using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Themes.Default;

namespace AgentOS.Frontend;

public static class ThemeManager
{
    public static void ApplyTheme(string themeName)
    {
        if (Application.Current == null) return;
        // Avalonia uses RequestedThemeVariant for Light/Dark
        Application.Current.RequestedThemeVariant = themeName.Equals("Dark", System.StringComparison.OrdinalIgnoreCase)
            ? Avalonia.Controls.ApplicationLifetimes.ThemeVariant.Dark
            : Avalonia.Controls.ApplicationLifetimes.ThemeVariant.Light;
    }
}
