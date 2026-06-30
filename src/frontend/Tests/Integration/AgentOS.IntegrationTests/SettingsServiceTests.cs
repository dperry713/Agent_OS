using System.Threading.Tasks;
using Grpc.Net.Client;
using Xunit;
using SettingsService; // Namespace from generated proto

namespace AgentOS.IntegrationTests;

public class SettingsServiceTests : IAsyncLifetime
{
    private GrpcChannel _channel;
    private SettingsService.SettingsServiceClient _client;

    public async Task InitializeAsync()
    {
        // Assumes the backend service is running on localhost:50051 (CI will start it).
        _channel = GrpcChannel.ForAddress("http://localhost:50051");
        _client = new SettingsService.SettingsServiceClient(_channel);
        await Task.CompletedTask;
    }

    public async Task DisposeAsync()
    {
        await _channel.ShutdownAsync();
    }

    [Fact]
    public async Task GetDarkThemeEnabled_ReturnsDefaultFalse()
    {
        var request = new GetDarkThemeEnabledRequest();
        var response = await _client.GetDarkThemeEnabledAsync(request);
        Assert.False(response.Enabled);
    }
}
