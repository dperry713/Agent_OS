using Microsoft.Extensions.DependencyInjection;
using AetherShell.Core.Interfaces;
using AetherShell.Core.Services;

namespace AetherShell.Core;

/// <summary>
/// Extension methods for configuring AetherShell services.
/// </summary>
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddAetherShellCore(this IServiceCollection services)
    {
        services.AddSingleton<IShellService, ShellService>();
        services.AddSingleton<MemoryService>();
        services.AddSingleton<IMemoryService>(sp => sp.GetRequiredService<MemoryService>());
        services.AddSingleton<IEventBus, EventBus>();
        services.AddSingleton<PolicyEngine>();
        services.AddSingleton<PowerShellRunner>();
        services.AddSingleton<GitRunner>();
        services.AddSingleton<ToolRouter>();
        return services;
    }
}