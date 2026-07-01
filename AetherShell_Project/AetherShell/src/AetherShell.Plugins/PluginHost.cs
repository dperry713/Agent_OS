using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;

namespace AetherShell.Plugins;

/// <summary>
/// Plugin discovery and hosting.
/// </summary>
public class PluginHost : IPluginHost
{
    private readonly Kernel _kernel;
    private readonly ILogger<PluginHost> _logger;
    private readonly List<IPlugin> _loadedPlugins = new();

    public PluginHost(Kernel kernel, ILogger<PluginHost> logger)
    {
        _kernel = kernel;
        _logger = logger;
    }

    public async Task LoadPluginsAsync()
    {
        _logger.LogInformation("Loading plugins...");
        var appDir = AppContext.BaseDirectory;
        var pluginsDir = Path.Combine(appDir, "Plugins");
        
        if (!Directory.Exists(pluginsDir))
        {
            Directory.CreateDirectory(pluginsDir);
        }

        var dllFiles = Directory.GetFiles(pluginsDir, "*.dll");
        foreach (var file in dllFiles)
        {
            try
            {
                var assembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(file);
                var pluginTypes = assembly.GetTypes()
                    .Where(t => typeof(IPlugin).IsAssignableFrom(t) && !t.IsInterface && !t.IsAbstract);

                foreach (var type in pluginTypes)
                {
                    var instance = Activator.CreateInstance(type) as IPlugin;
                    if (instance != null)
                    {
                        await instance.InitializeAsync();
                        _loadedPlugins.Add(instance);
                        var plugin = KernelPluginFactory.CreateFromObject(instance, instance.Name);
                        _kernel.Plugins.Add(plugin);
                        _logger.LogInformation("Loaded plugin: {PluginName} v{Version}", instance.Name, instance.Version);
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to load plugin from {File}", file);
            }
        }

        // Also register any already available via executing assembly (e.g. ExamplePlugin)
        var localPluginTypes = Assembly.GetExecutingAssembly().GetTypes()
            .Where(t => typeof(IPlugin).IsAssignableFrom(t) && !t.IsInterface && !t.IsAbstract);
            
        foreach(var type in localPluginTypes)
        {
            if (_loadedPlugins.Any(p => p.GetType() == type)) continue;
            var instance = Activator.CreateInstance(type) as IPlugin;
            if (instance != null)
            {
                await instance.InitializeAsync();
                _loadedPlugins.Add(instance);
                var plugin = KernelPluginFactory.CreateFromObject(instance, instance.Name);
                _kernel.Plugins.Add(plugin);
                _logger.LogInformation("Loaded built-in plugin: {PluginName} v{Version}", instance.Name, instance.Version);
            }
        }
        
        _logger.LogInformation("Loaded {Count} plugins.", _loadedPlugins.Count);
    }

    public Task<IEnumerable<IPlugin>> GetPluginsAsync()
    {
        return Task.FromResult<IEnumerable<IPlugin>>(_loadedPlugins);
    }
}