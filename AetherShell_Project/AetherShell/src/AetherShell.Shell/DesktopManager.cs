using System.Runtime.InteropServices;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;

namespace AetherShell.Shell;

/// <summary>
/// Controls desktop background, icons, widgets.
/// </summary>
public class DesktopManager : IDesktopManager
{
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    private static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);

    private const int SPI_SETDESKWALLPAPER = 20;
    private const int SPIF_UPDATEINIFILE = 0x01;
    private const int SPIF_SENDWININICHANGE = 0x02;

    public Task ActivateAsync()
    {
        return Task.CompletedTask;
    }

    public Task SetWallpaperAsync(string path)
    {
        SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, path, SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE);
        return Task.CompletedTask;
    }
}
