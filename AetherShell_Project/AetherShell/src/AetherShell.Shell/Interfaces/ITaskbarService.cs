namespace AetherShell.Shell.Interfaces;

/// <summary>
/// Taskbar and launcher orchestration.
/// </summary>
public interface ITaskbarService
{
    void ShowCommandPalette();
    void PinApplication(string appId);
}