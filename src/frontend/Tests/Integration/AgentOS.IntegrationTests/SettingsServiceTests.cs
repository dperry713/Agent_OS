using System.Threading.Tasks;
using Xunit;
using AgentOS.Frontend.Services;

namespace AgentOS.IntegrationTests;

public class SettingsServiceTests : IAsyncLifetime
{
    private SettingsService _settingsService;

    public async Task InitializeAsync()
    {
        _settingsService = new SettingsService();
        await Task.CompletedTask;
    }

    public Task DisposeAsync()
    {
        // No resources to dispose
        return Task.CompletedTask;
    }

    [Fact]
    public void GetDarkThemeEnabled_ReturnsDefaultFalse()
    {
        var result = _settingsService.GetDarkThemeEnabled();
        Assert.False(result);
    }
}
