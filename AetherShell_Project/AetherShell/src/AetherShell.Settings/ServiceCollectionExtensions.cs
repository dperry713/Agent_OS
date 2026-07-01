using Microsoft.Extensions.DependencyInjection;

namespace AetherShell.Settings;

/// <summary>
/// Extension methods for configuring AetherShell Settings services.
/// </summary>
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddAetherShellSettings(this IServiceCollection services)
    {
        services.AddTransient<SettingsPage>();
        return services;
    }
}
