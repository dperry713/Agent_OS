using Microsoft.UI.Xaml;
using AetherShell.Core.Interfaces;
using AetherShell.Automation.Monitors;
using Microsoft.Extensions.DependencyInjection;
using System;

namespace AetherShell.App;

/// <summary>
/// Main application entry point.
/// </summary>
public partial class App : Application
{
    private readonly IShellService    _shellService;
    private readonly IServiceProvider _serviceProvider;
    private MainWindow? _window;

    public static IServiceProvider Services { get; private set; } = null!;

    public App(IShellService shellService, IServiceProvider serviceProvider)
    {
        _shellService    = shellService;
        _serviceProvider = serviceProvider;
        Services         = serviceProvider;
        this.InitializeComponent();
    }

    protected override async void OnLaunched(LaunchActivatedEventArgs args)
    {
        await _shellService.InitializeAsync();

        // Start background monitors (done here to avoid circular Core → Automation dependency)
        var metrics   = _serviceProvider.GetRequiredService<SystemMetricsMonitor>();
        var scheduler = _serviceProvider.GetRequiredService<ScheduledEventSource>();
        var fsMonitor = _serviceProvider.GetRequiredService<FileSystemMonitor>();
        var regMon    = _serviceProvider.GetRequiredService<RegistryMonitor>();

        metrics.Start(TimeSpan.FromSeconds(60));
        fsMonitor.Start();
        regMon.Start(TimeSpan.FromSeconds(30));

        scheduler.Register("SystemHealthCheck", "Periodic health check", TimeSpan.FromMinutes(1));
        scheduler.Register("MemoryCleanup",     "Memory housekeeping",   TimeSpan.FromMinutes(10));
        scheduler.Start();

        _window = _serviceProvider.GetRequiredService<MainWindow>();
        _window.Activate();
    }
}