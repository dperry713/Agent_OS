using Xunit;
using Moq;
using AetherShell.AI.RAG;
using AetherShell.Core.Interfaces;

namespace AetherShell.Tests.Unit.AI;

public class RagServiceTests
{
    [Fact]
    public async Task QueryAsync_ReturnsResponse()
    {
        var memoryMock = new Mock<IMemoryService>();
        var service = new RagService(memoryMock.Object);
        var result = await service.QueryAsync("test query");
        Assert.Contains("AI Response", result);
    }
}