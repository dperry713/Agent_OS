using Xunit;
using Moq;
using AetherShell.Core.Services;
using AetherShell.Core.Interfaces;
using Microsoft.Extensions.Logging;

namespace AetherShell.Tests.Unit.Core;

public class ShellServiceTests
{
    [Fact]
    public async Task InitializeAsync_CallsDesktopManager()
    {
        // Arrange
        var loggerMock    = new Mock<ILogger<ShellService>>();
        var desktopMock   = new Mock<IDesktopManager>();
        var eventBusMock  = new Mock<IEventBus>();
        var mcpLoggerMock = new Mock<ILogger<McpClient>>();
        var pluginHostMock = new Mock<IPluginHost>();
        var mcpClient     = new McpClient(mcpLoggerMock.Object);
        var service       = new ShellService(loggerMock.Object, desktopMock.Object, eventBusMock.Object, mcpClient, pluginHostMock.Object);

        // Act
        await service.InitializeAsync();

        // Assert
        desktopMock.Verify(d => d.ActivateAsync(), Times.Once);
    }
}