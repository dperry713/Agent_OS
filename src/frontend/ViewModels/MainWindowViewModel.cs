using System;
using System.Threading.Tasks;
using Grpc.Net.Client;
using Grpc.Core;
using Agentos.Core;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Extensions.Options;

using Dock.Model.Controls;
using Dock.Model.Core;

namespace AgentOS.Desktop.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    [ObservableProperty]
    private IFactory? _factory;

    [ObservableProperty]
    private IRootDock? _layout;

    [ObservableProperty]
    private string _greeting = "Connecting to AgentOS Kernel...";

    [ObservableProperty]
    private bool _isCustomShellEnabled = false;

    private CoreIpc.CoreIpcClient? _client;



    // Default constructor for designer
    public MainWindowViewModel() : this(Options.Create(new KernelSettings()))
    {
    }

    [RelayCommand]
    private async Task ToggleShellAsync()
    {
        if (_client == null) return;
        try
        {
            var newStatus = !IsCustomShellEnabled;
            var reply = await _client.ToggleCustomShellAsync(new ToggleShellRequest { Enable = newStatus });
            IsCustomShellEnabled = reply.IsEnabled;
            Greeting = reply.Message;
        }
        catch (System.Exception ex)
        {
            Greeting = $"Failed to toggle shell: {ex.Message}";
        }
    }

    public MainWindowViewModel(IOptions<KernelSettings> kernelSettings)
    {
        Factory = new MainDockFactory();
        Layout = Factory.CreateLayout();
        if (Layout != null)
        {
            Factory.InitLayout(Layout);
        }

        var endpoint = kernelSettings.Value.GrpcEndpoint;
        Task.Run(async () =>
        {
            try
            {
                AppContext.SetSwitch("System.Net.Http.SocketsHttpHandler.Http2UnencryptedSupport", true);
                var channel = GrpcChannel.ForAddress(endpoint, new GrpcChannelOptions { Credentials = ChannelCredentials.Insecure });
                _client = new CoreIpc.CoreIpcClient(channel);
                var reply = await _client.PingAsync(new PingRequest { Message = "Avalonia" });
                Greeting = $"Connected to {endpoint}: {reply.Message}";

                var shellStatus = await _client.IsCustomShellEnabledAsync(new EmptyRequest());
                IsCustomShellEnabled = shellStatus.IsEnabled;
            }
            catch (System.Exception ex)
            {
                Greeting = $"Failed to connect to {endpoint}: {ex.Message}";
            }
        });
    }
        {
            var newStatus = !IsCustomShellEnabled;
            var reply = await _client.ToggleCustomShellAsync(new ToggleShellRequest { Enable = newStatus });
            IsCustomShellEnabled = reply.IsEnabled;
            Greeting = reply.Message;
        }
        catch (System.Exception ex)
        {
            Greeting = $"Failed to toggle shell: {ex.Message}";
        }
    }
}
