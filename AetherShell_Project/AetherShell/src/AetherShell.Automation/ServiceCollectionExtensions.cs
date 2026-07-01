using System;
using Microsoft.Extensions.DependencyInjection;
using AetherShell.Automation.Monitors;

namespace AetherShell.Automation;

/// <summary>
/// Extension methods for configuring AetherShell Automation services.
/// </summary>
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddAetherShellAutomation(this IServiceCollection services)
    {
        services.AddSingleton<WorkflowEngine>();
        services.AddSingleton<ExecutionEngine>();
        services.AddSingleton<SystemMetricsMonitor>();
        services.AddSingleton<ScheduledEventSource>();
        services.AddSingleton<FileSystemMonitor>(sp =>
        {
            var logger = sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<FileSystemMonitor>>();
            var bus    = sp.GetRequiredService<AetherShell.Core.Interfaces.IEventBus>();
            var downloads = System.IO.Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
            return new FileSystemMonitor(logger, bus, downloads);
        });
        services.AddSingleton<RegistryMonitor>();
        return services;
    }
}
