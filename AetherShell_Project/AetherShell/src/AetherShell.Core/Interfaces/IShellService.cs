using System.Threading.Tasks;

namespace AetherShell.Core.Interfaces;

/// <summary>
/// Core shell service contract.
/// </summary>
public interface IShellService
{
    Task InitializeAsync();
    Task ShutdownAsync();
    // Window management, desktop control, etc.
}