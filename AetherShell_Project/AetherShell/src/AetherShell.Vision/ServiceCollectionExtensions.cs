using Microsoft.Extensions.DependencyInjection;

namespace AetherShell.Vision;

/// <summary>
/// Extension methods for configuring AetherShell Vision services.
/// </summary>
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddAetherShellVision(this IServiceCollection services)
    {
        services.AddSingleton<ScreenAnalyzer>();
        return services;
    }
}
