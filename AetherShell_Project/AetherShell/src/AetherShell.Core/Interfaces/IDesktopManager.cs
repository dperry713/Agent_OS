using System.Threading.Tasks;

namespace AetherShell.Core.Interfaces;

/// <summary>
/// Controls desktop background, icons, widgets.
/// </summary>
public interface IDesktopManager
{
    Task ActivateAsync();
    Task SetWallpaperAsync(string path);
    // Widget management, etc.
}
