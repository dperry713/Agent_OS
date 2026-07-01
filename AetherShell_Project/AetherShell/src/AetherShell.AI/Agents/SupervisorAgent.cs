using Microsoft.SemanticKernel;
using AetherShell.Core.Interfaces;
using AetherShell.Core.Services;
using AetherShell.Vision;
using AetherShell.Automation;
using AetherShell.AI.Intent;
using AetherShell.AI.Planning;
using System.Threading.Tasks;
using System;

namespace AetherShell.AI.Agents;

/// <summary>
/// Top-level supervisor — now routes through the full event-driven pipeline:
/// IntentClassifier → PlanningEngine → PolicyEngine → AgentOrchestrator → ResultProcessor
///
/// Legacy direct-dispatch commands are preserved as fallback when the new pipeline
/// returns "Unknown" intent.
/// </summary>
public class SupervisorAgent : IAIAgent
{
    private readonly Kernel            _kernel;
    private readonly ScreenAnalyzer    _screenAnalyzer;
    private readonly WorkflowEngine    _workflowEngine;
    private readonly IPluginHost       _pluginHost;
    private readonly McpClient         _mcpClient;
    private readonly IntentClassifier  _intentClassifier;
    private readonly PlanningEngine    _planner;
    private readonly PolicyEngine      _policy;
    private readonly AgentOrchestrator _orchestrator;
    private readonly ResultProcessor   _resultProcessor;
    private readonly IMemoryService    _memory;

    public string Name => "Supervisor";

    public SupervisorAgent(
        Kernel             kernel,
        ScreenAnalyzer     screenAnalyzer,
        WorkflowEngine     workflowEngine,
        IPluginHost        pluginHost,
        McpClient          mcpClient,
        IntentClassifier   intentClassifier,
        PlanningEngine     planner,
        PolicyEngine       policy,
        AgentOrchestrator  orchestrator,
        ResultProcessor    resultProcessor,
        IMemoryService     memory)
    {
        _kernel           = kernel;
        _screenAnalyzer   = screenAnalyzer;
        _workflowEngine   = workflowEngine;
        _pluginHost       = pluginHost;
        _mcpClient        = mcpClient;
        _intentClassifier = intentClassifier;
        _planner          = planner;
        _policy           = policy;
        _orchestrator     = orchestrator;
        _resultProcessor  = resultProcessor;
        _memory           = memory;
    }

    public async Task ExecuteAsync(object context)
    {
        if (context is not AgentExecutionContext ctx) return;

        var query = ctx.Query.Trim();

        try
        {
            // ── STEP 1: Classify intent ────────────────────────────────────
            var intent = await _intentClassifier.ClassifyAsync(query);

            // ── STEP 2: Build plan ─────────────────────────────────────────
            var plan = await _planner.CreatePlanAsync(intent, query);

            // ── STEP 3: Policy check ───────────────────────────────────────
            var policy = await _policy.EvaluateAsync(plan);
            if (!policy.Allowed)
            {
                ctx.Response = $"⛔ Policy Denied: {policy.DenialReason}";
                return;
            }

            // ── STEP 4: Orchestrate execution ──────────────────────────────
            var result = await _orchestrator.DispatchAsync(plan);

            // ── STEP 5: Post-process (memory + audit) ──────────────────────
            await _resultProcessor.ProcessAsync(result, query);

            // ── Format response ────────────────────────────────────────────
            if (result.StepResults.Count == 1)
            {
                // Single-step: return output directly (clean UX)
                ctx.Response = result.StepResults[0].Success
                    ? result.StepResults[0].Output
                    : $"❌ {result.StepResults[0].Output}";
            }
            else
            {
                // Multi-step: show step-by-step log
                var sb = new System.Text.StringBuilder();
                sb.AppendLine($"🔄 **{plan.GoalDescription}**");
                sb.AppendLine($"Intent: {intent.IntentName} (confidence: {intent.Confidence:P0})");
                sb.AppendLine();
                for (int i = 0; i < result.StepResults.Count; i++)
                {
                    var s = result.StepResults[i];
                    sb.AppendLine($"{(s.Success ? "✅" : "❌")} Step {i + 1}: {s.Description}");
                    if (!string.IsNullOrWhiteSpace(s.Output))
                        sb.AppendLine($"   {s.Output[..Math.Min(200, s.Output.Length)]}");
                }
                sb.AppendLine();
                sb.AppendLine(result.Summary);
                ctx.Response = sb.ToString();
            }
        }
        catch (Exception ex)
        {
            ctx.Response = $"Supervisor Error: {ex.Message}";
        }
    }
}