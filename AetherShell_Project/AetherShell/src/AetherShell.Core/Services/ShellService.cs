using System;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;
using Microsoft.Extensions.Logging;

namespace AetherShell.Core.Services;

/// <summary>
/// Default implementation of shell lifecycle.
/// Starts MCP client on initialization; monitors are started by the App host to avoid circular deps.
/// </summary>
public class ShellService : IShellService
{
    private readonly ILogger<ShellService> _logger;
    private readonly IDesktopManager       _desktopManager;
    private readonly IEventBus             _eventBus;
    private readonly McpClient             _mcpClient;
    private readonly IPluginHost           _pluginHost;

    public ShellService(
        ILogger<ShellService> logger,
        IDesktopManager       desktopManager,
        IEventBus             eventBus,
        McpClient             mcpClient,
        IPluginHost           pluginHost)
    {
        _logger         = logger;
        _desktopManager = desktopManager;
        _eventBus       = eventBus;
        _mcpClient      = mcpClient;
        _pluginHost     = pluginHost;
    }

    public async Task InitializeAsync()
    {
        _logger.LogInformation("AetherShell initializing...");
        await _desktopManager.ActivateAsync();

        // Load dynamic plugins
        await _pluginHost.LoadPluginsAsync();

        // Start MCP client connection to AgentOS
        _mcpClient.Start();

        // Publish ShellInitialized event
        await _eventBus.PublishAsync(new ShellInitializedEvent());
        _logger.LogInformation("AetherShell initialized.");
    }

    public Task ShutdownAsync()
    {
        _logger.LogInformation("AetherShell shutting down...");
        return Task.CompletedTask;
    }
}

public record ShellInitializedEvent();