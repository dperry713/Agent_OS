using Xunit;
using Microsoft.Extensions.DependencyInjection;
using AetherShell.Settings;
using System.Linq;

namespace AetherShell.Tests.Unit.Settings;

public class SettingsServiceTests
{
    [Fact]
    public void AddAetherShellSettings_RegistersSettingsPageAsTransient()
    {
        // Arrange
        var services = new ServiceCollection();

        // Act
        services.AddAetherShellSettings();

        // Assert
        var descriptor = services.FirstOrDefault(d => d.ServiceType == typeof(SettingsPage));
        Assert.NotNull(descriptor);
        Assert.Equal(ServiceLifetime.Transient, descriptor.Lifetime);
    }
}
