using Microsoft.Extensions.DependencyInjection;
using AetherShell.Core.Interfaces;

namespace AetherShell.Plugins;

/// <summary>
/// Extension methods for configuring AetherShell Plugins services.
/// </summary>
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddAetherShellPlugins(this IServiceCollection services)
    {
        services.AddSingleton<IPluginHost, PluginHost>();
        services.AddTransient<ExamplePlugin>();
        return services;
    }
}
