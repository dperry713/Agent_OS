using System.Threading.Tasks;

namespace AetherShell.Core.Interfaces;

/// <summary>
/// Plugin system host and discovery.
/// </summary>
public interface IPluginHost
{
    Task LoadPluginsAsync();
    Task<IEnumerable<IPlugin>> GetPluginsAsync();
}