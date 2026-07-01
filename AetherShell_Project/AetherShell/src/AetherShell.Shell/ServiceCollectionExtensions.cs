using Microsoft.Extensions.DependencyInjection;
using AetherShell.Core.Interfaces;

namespace AetherShell.Shell;

/// <summary>
/// Extension methods for configuring AetherShell UI/Shell services.
/// </summary>
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddAetherShellUI(this IServiceCollection services)
    {
        services.AddSingleton<IDesktopManager, DesktopManager>();
        return services;
    }
}
