using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using AetherShell.Core;
using AetherShell.AI;
using AetherShell.Plugins;
using AetherShell.Shell;
using AetherShell.Automation;
using AetherShell.Platform;
using AetherShell.Vision;
using AetherShell.Settings;

namespace AetherShell.App;

public class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        WinRT.ComWrappersSupport.InitializeComWrappers();

        Microsoft.UI.Xaml.Application.Start((p) =>
        {
            var context = new Microsoft.UI.Dispatching.DispatcherQueueSynchronizationContext(
                Microsoft.UI.Dispatching.DispatcherQueue.GetForCurrentThread());
            System.Threading.SynchronizationContext.SetSynchronizationContext(context);

            var host = Host.CreateDefaultBuilder(args)
                .ConfigureServices(services =>
                {
                    services.AddAetherShellCore();
                    services.AddAetherShellAI();
                    services.AddAetherShellPlugins();
                    services.AddAetherShellUI();
                    services.AddAetherShellAutomation();
                    services.AddAetherShellPlatform();
                    services.AddAetherShellVision();
                    services.AddAetherShellSettings();
                    services.AddSingleton<AetherShell.Core.Services.McpClient>();
                    services.AddSingleton<AetherShell.App.Services.VoiceService>();
                    services.AddSingleton<AetherShell.Core.Interfaces.IVoiceService>(sp =>
                        sp.GetRequiredService<AetherShell.App.Services.VoiceService>());
                    services.AddSingleton<MainWindow>();
                    services.AddTransient<CommandPalette>();
                    services.AddSingleton<App>();
                })
                .Build();

            var app = host.Services.GetRequiredService<App>();
        });
    }
}