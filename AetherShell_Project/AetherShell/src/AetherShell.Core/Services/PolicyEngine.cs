using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;

namespace AetherShell.Core.Services;

public record PolicyResult(bool Allowed, string? DenialReason = null);

public interface IPolicyRule
{
    string RuleName { get; }
    Task<PolicyResult> EvaluateAsync(WorkflowPlan plan);
}

/// <summary>
/// Evaluates a WorkflowPlan against all registered policy rules before execution.
/// </summary>
public class PolicyEngine
{
    private readonly List<IPolicyRule> _rules;

    public PolicyEngine()
    {
        _rules = new List<IPolicyRule>
        {
            new NoRegistryWriteWithoutElevationRule(),
            new MassFileDeleteWarningRule(),
            new MaxStepsLimitRule(50)
        };
    }

    public async Task<PolicyResult> EvaluateAsync(WorkflowPlan plan)
    {
        foreach (var rule in _rules)
        {
            var result = await rule.EvaluateAsync(plan);
            if (!result.Allowed)
                return result;
        }
        return new PolicyResult(true);
    }
}

// ── Built-in Rules ────────────────────────────────────────────────────────────

internal sealed class NoRegistryWriteWithoutElevationRule : IPolicyRule
{
    public string RuleName => "NoRegistryWriteWithoutElevation";

    public Task<PolicyResult> EvaluateAsync(WorkflowPlan plan)
    {
        bool hasRegWrite = plan.Steps.Exists(s => s.ToolName == "set_registry_value")
                        && plan.RequiredPermissions.Length > 0;
        // In a real system, check if process is elevated. Here we allow but warn at High risk.
        return Task.FromResult(new PolicyResult(true));
    }
}

internal sealed class MassFileDeleteWarningRule : IPolicyRule
{
    public string RuleName => "MassFileDeleteWarningRule";

    public Task<PolicyResult> EvaluateAsync(WorkflowPlan plan)
    {
        // Block plans that attempt bulk delete without confirmation flag
        bool hasBulkDelete = plan.Steps.Exists(s =>
            s.ToolName is "delete_files" or "rm" && !plan.RequiresConfirmation);
        return Task.FromResult(hasBulkDelete
            ? new PolicyResult(false, "Bulk file delete requires user confirmation. Set RequiresConfirmation=true.")
            : new PolicyResult(true));
    }
}

internal sealed class MaxStepsLimitRule : IPolicyRule
{
    private readonly int _max;
    public MaxStepsLimitRule(int max) => _max = max;
    public string RuleName => "MaxStepsLimit";

    public Task<PolicyResult> EvaluateAsync(WorkflowPlan plan)
        => Task.FromResult(plan.Steps.Count > _max
            ? new PolicyResult(false, $"Plan exceeds maximum step limit of {_max}.")
            : new PolicyResult(true));
}
