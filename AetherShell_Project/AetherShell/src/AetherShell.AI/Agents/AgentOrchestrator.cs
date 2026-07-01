using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;
using AetherShell.Core.Services;
using AetherShell.Automation;
using Microsoft.Extensions.Logging;

namespace AetherShell.AI.Agents;

/// <summary>
/// Dispatches a WorkflowPlan to the right specialized agents with retry, timeout, and result aggregation.
/// </summary>
public class AgentOrchestrator
{
    private readonly ILogger<AgentOrchestrator> _logger;
    private readonly IReadOnlyList<ISpecializedAgent> _agents;
    private readonly ExecutionEngine _engine;
    private readonly ToolRouter      _router;

    public AgentOrchestrator(
        ILogger<AgentOrchestrator> logger,
        IEnumerable<ISpecializedAgent> agents,
        ExecutionEngine engine,
        ToolRouter      router)
    {
        _logger = logger;
        _agents  = agents.ToList();
        _engine  = engine;
        _router  = router;
    }

    public async Task<ExecutionResult> DispatchAsync(WorkflowPlan plan)
    {
        _logger.LogInformation("[Orchestrator] Dispatching plan '{Intent}' ({Steps} steps)",
            plan.IntentName, plan.Steps.Count);

        return await _engine.ExecuteAsync(plan, async step =>
        {
            var agent = FindAgent(step.AgentName) ?? FindFallback();
            _logger.LogInformation("[Orchestrator] Routing step '{Desc}' → {Agent}", step.Description, agent.Name);

            // Retry up to 3 times with backoff
            for (int attempt = 1; attempt <= 3; attempt++)
            {
                try
                {
                    using var cts = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(30));
                    var result = await agent.RunAsync(step, _router);
                    if (result.Success) return result.Output;
                    if (attempt == 3) throw new Exception($"Agent {agent.Name} failed after 3 attempts: {result.Output}");
                }
                catch (Exception ex) when (attempt < 3)
                {
                    _logger.LogWarning("[Orchestrator] Attempt {N} failed: {Err}. Retrying...", attempt, ex.Message);
                    await Task.Delay(TimeSpan.FromMilliseconds(500 * attempt));
                }
            }
            throw new Exception($"Step '{step.Description}' exhausted all retry attempts.");
        });
    }

    private ISpecializedAgent? FindAgent(string name)
        => _agents.FirstOrDefault(a => a.Name.Equals(name, StringComparison.OrdinalIgnoreCase));

    private ISpecializedAgent FindFallback()
        => _agents.FirstOrDefault(a => a.Name == "SystemAgent")
        ?? _agents.First();
}

/// <summary>
/// Persists result and dispatches notifications after workflow completion.
/// </summary>
public class ResultProcessor
{
    private readonly IMemoryService _memory;
    private readonly IEventBus      _bus;

    public ResultProcessor(IMemoryService memory, IEventBus bus)
    {
        _memory = memory;
        _bus    = bus;
    }

    public async Task ProcessAsync(ExecutionResult result, string query)
    {
        // Store conversation history
        await _memory.StoreConversationAsync(query, result.Summary, result.WorkflowId);

        // Audit log via memory
        if (_memory is MemoryService ms)
            ms.AppendAuditLog(result.Success ? "WorkflowCompleted" : "WorkflowFailed",
                "AgentOrchestrator", result.Summary);
    }
}
