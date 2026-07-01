using Xunit;
using Moq;
using AetherShell.Core.Services;
using Microsoft.Extensions.Logging;

namespace AetherShell.Tests.Unit.Core;

public class MemoryServiceTests
{
    private static MemoryService CreateService()
    {
        var logger = new Mock<ILogger<MemoryService>>().Object;
        return new MemoryService(logger);
    }

    [Fact]
    public async Task StoreAndRetrieve_Works()
    {
        var service = CreateService();
        await service.StoreAsync("test-key", new { Value = "hello" });
        var result = await service.RetrieveAsync<System.Text.Json.JsonElement>("test-key");
        Assert.Equal("hello", result.GetProperty("Value").GetString());
    }

    [Fact]
    public async Task StoreConversation_And_GetHistory_Works()
    {
        var service = CreateService();
        await service.StoreConversationAsync("what is the weather?", "It is sunny.");
        var history = await service.GetConversationHistoryAsync(10);
        Assert.Contains(history, h => h.Query == "what is the weather?");
    }

    [Fact]
    public async Task StoreOutcome_And_GetWorkflowHistory_Works()
    {
        var service = CreateService();
        await service.StoreOutcomeAsync("wf-001", "TestWorkflow", true, "Completed OK");
        var outcomes = await service.GetWorkflowHistoryAsync(5);
        Assert.Contains(outcomes, o => o.WorkflowId == "wf-001" && o.Success);
    }
}