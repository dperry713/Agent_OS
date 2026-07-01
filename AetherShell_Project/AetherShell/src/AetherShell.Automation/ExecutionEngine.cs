using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using AetherShell.Core.Events;
using AetherShell.Core.Interfaces;
using Microsoft.Extensions.Logging;

namespace AetherShell.Automation;

public enum ExecutionState { Pending, Running, Checkpointing, Completed, Failed, RollingBack, RolledBack }

public record ExecutionResult(string WorkflowId, bool Success, string Summary, TimeSpan Duration,
    List<StepResult> StepResults);
public record StepResult(string StepId, string Description, bool Success, string Output, TimeSpan Duration);

/// <summary>
/// Transactional execution engine with per-step checkpoints and rollback.
/// State machine: Pending → Running → (Checkpointing → Running)* → Completed | Failed → RollingBack → RolledBack
/// </summary>
public class ExecutionEngine
{
    private readonly ILogger<ExecutionEngine>  _logger;
    private readonly IEventBus                 _bus;
    private readonly IMemoryService            _memory;

    public ExecutionEngine(ILogger<ExecutionEngine> logger, IEventBus bus, IMemoryService memory)
    {
        _logger = logger;
        _bus    = bus;
        _memory = memory;
    }

    public ExecutionState CurrentState { get; private set; } = ExecutionState.Pending;

    /// <summary>
    /// Execute a WorkflowPlan. Each step result is checkpointed. On failure, rollback steps run in reverse.
    /// </summary>
    public async Task<ExecutionResult> ExecuteAsync(WorkflowPlan plan,
        Func<TaskStep, Task<string>> stepExecutor)
    {
        var workflowId   = plan.PlanId;
        var stepResults  = new List<StepResult>();
        var startTime    = DateTime.UtcNow;
        CurrentState     = ExecutionState.Running;

        await _bus.PublishAsync(new WorkflowStartedEvent(workflowId, plan.IntentName));

        try
        {
            for (int i = 0; i < plan.Steps.Count; i++)
            {
                var step = plan.Steps[i];
                var stepStart = DateTime.UtcNow;

                _logger.LogInformation("[ExecutionEngine] Step {N}/{Total}: {Desc}", i + 1, plan.Steps.Count, step.Description);

                string output;
                bool   success;
                try
                {
                    output  = await stepExecutor(step);
                    success = true;
                }
                catch (Exception ex)
                {
                    output  = $"STEP ERROR: {ex.Message}";
                    success = false;
                    _logger.LogWarning("[ExecutionEngine] Step {N} failed: {Err}", i + 1, ex.Message);
                }

                var stepResult = new StepResult(step.StepId, step.Description, success, output,
                    DateTime.UtcNow - stepStart);
                stepResults.Add(stepResult);

                // Checkpoint after each step
                CurrentState = ExecutionState.Checkpointing;
                await SaveCheckpointAsync(workflowId, i, stepResults);
                await _bus.PublishAsync(new WorkflowStepCompletedEvent(workflowId, i, step.Description, output));
                CurrentState = ExecutionState.Running;

                if (!success)
                {
                    // Trigger rollback
                    CurrentState = ExecutionState.Failed;
                    await RunRollbackAsync(plan, stepExecutor);
                    var failDuration = DateTime.UtcNow - startTime;
                    await _bus.PublishAsync(new WorkflowFailedEvent(workflowId, step.Description, output, RolledBack: true));
                    await _memory.StoreOutcomeAsync(workflowId, plan.IntentName, false,
                        $"Failed at step {i + 1}: {step.Description}. Rolled back.");
                    return new ExecutionResult(workflowId, false,
                        $"❌ Failed at step {i + 1}: {step.Description}\n{output}", failDuration, stepResults);
                }
            }

            CurrentState     = ExecutionState.Completed;
            var totalDuration = DateTime.UtcNow - startTime;
            var summary      = $"✅ Completed {plan.Steps.Count} step(s) in {totalDuration.TotalSeconds:F1}s";
            await _bus.PublishAsync(new WorkflowCompletedEvent(workflowId, plan.IntentName, summary, totalDuration));
            await _memory.StoreOutcomeAsync(workflowId, plan.IntentName, true, summary);
            _logger.LogInformation("[ExecutionEngine] Workflow {Id} completed.", workflowId);
            return new ExecutionResult(workflowId, true, summary, totalDuration, stepResults);
        }
        catch (Exception ex)
        {
            CurrentState = ExecutionState.Failed;
            _logger.LogError(ex, "[ExecutionEngine] Unhandled error in workflow {Id}", workflowId);
            await _bus.PublishAsync(new WorkflowFailedEvent(workflowId, "unknown", ex.Message, RolledBack: false));
            return new ExecutionResult(workflowId, false, $"Unhandled error: {ex.Message}",
                DateTime.UtcNow - startTime, stepResults);
        }
    }

    private async Task RunRollbackAsync(WorkflowPlan plan, Func<TaskStep, Task<string>> executor)
    {
        if (plan.RollbackSteps.Count == 0) return;
        CurrentState = ExecutionState.RollingBack;
        _logger.LogWarning("[ExecutionEngine] Running {N} rollback steps.", plan.RollbackSteps.Count);

        for (int i = plan.RollbackSteps.Count - 1; i >= 0; i--)
        {
            try { await executor(plan.RollbackSteps[i]); }
            catch (Exception ex) { _logger.LogWarning("Rollback step failed: {Err}", ex.Message); }
        }
        CurrentState = ExecutionState.RolledBack;
    }

    private async Task SaveCheckpointAsync(string workflowId, int stepIndex, List<StepResult> results)
    {
        await _memory.StoreAsync($"checkpoint:{workflowId}:{stepIndex}",
            new { StepIndex = stepIndex, CompletedSteps = results.Count }, "checkpoints");
    }
}
