using System.Collections.Generic;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;
using AetherShell.Core.Services;

namespace AetherShell.Core.Interfaces;

public record AgentResult(bool Success, string Output, string AgentName);

public record AgentCapabilities(bool CanRead, bool CanWrite, bool CanExecute, bool CanLaunch);

/// <summary>
/// Contract for all domain-specific specialized agents.
/// </summary>
public interface ISpecializedAgent
{
    string   Name            { get; }
    string[] SupportedIntents { get; }
    AgentCapabilities Capabilities { get; }
    Task<AgentResult> RunAsync(TaskStep step, ToolRouter router);
}
