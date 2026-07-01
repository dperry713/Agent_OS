using Microsoft.Extensions.DependencyInjection;

namespace AetherShell.Platform;

/// <summary>
/// Extension methods for configuring AetherShell Platform-specific services.
/// </summary>
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddAetherShellPlatform(this IServiceCollection services)
    {
        // Future: Register platform services like Windows.Graphics.Capture, registry keys, etc.
        return services;
    }
}
