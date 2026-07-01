using System.Threading.Tasks;

namespace AetherShell.Core.Interfaces;

/// <summary>
/// Defines a plugin extension.
/// </summary>
public interface IPlugin
{
    string Name { get; }
    string Version { get; }
    Task InitializeAsync();
}
