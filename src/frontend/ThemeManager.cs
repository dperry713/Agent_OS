using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Styling;

namespace AgentOS.Frontend;

public static class ThemeManager
{
    public static void ApplyTheme(string themeName)
    {
        if (Application.Current == null) return;
        // Avalonia uses RequestedThemeVariant for Light/Dark
        Application.Current.RequestedThemeVariant = themeName.Equals("Dark", System.StringComparison.OrdinalIgnoreCase)
            ? ThemeVariant.Dark
            : ThemeVariant.Light;
    }
}
