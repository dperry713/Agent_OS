using Avalonia;
using System;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using Microsoft.Extensions.Logging;
using OpenTelemetry;
using OpenTelemetry.Logs;
using OpenTelemetry.Trace;
using OpenTelemetry.Metrics;
using AgentOS.Desktop.ViewModels;

namespace AgentOS.Desktop;

sealed class Program
{
    public static IServiceProvider? Services { get; private set; }
    public static IConfiguration? Configuration { get; private set; }

    [STAThread]
    public static void Main(string[] args)
    {
        var configuration = new ConfigurationBuilder()
            .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
            .AddEnvironmentVariables()
            .Build();

        Configuration = configuration;

        var services = new ServiceCollection();
        
        services.Configure<KernelSettings>(configuration.GetSection("Kernel"));

        // Setup OpenTelemetry Logging and Tracing
        services.AddLogging(logging =>
        {
            logging.AddOpenTelemetry(options =>
            {
                options.AddOtlpExporter();
                options.AddConsoleExporter();
            });
        });

        services.AddOpenTelemetry()
            .WithTracing(tracerProviderBuilder =>
            {
                tracerProviderBuilder
                    .AddSource("AgentOS.Desktop")
                    .AddOtlpExporter();
            });

        // Register ViewModels
        services.AddTransient<MainWindowViewModel>();

        Services = services.BuildServiceProvider();

        BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
    }

    public static AppBuilder BuildAvaloniaApp()
        => AppBuilder.Configure<App>()
            .UsePlatformDetect()
        .UseSkia()
        .UseWin32()
#if DEBUG
            .WithDeveloperTools()
#endif
            .WithInterFont()
            .LogToTrace();
}
