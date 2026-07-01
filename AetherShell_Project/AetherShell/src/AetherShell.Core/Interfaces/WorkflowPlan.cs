using System;
using System.Collections.Generic;

namespace AetherShell.Core.Interfaces;

public enum RiskLevel { Low, Medium, High, Critical }

/// <summary>
/// A single executable step within a workflow plan.
/// Lives in Core so both AI and Automation can reference it without circular deps.
/// </summary>
public record TaskStep
{
    public string StepId     { get; init; } = Guid.NewGuid().ToString("N")[..8];
    public string AgentName  { get; init; } = string.Empty;
    public string ToolName   { get; init; } = string.Empty;
    public Dictionary<string, string> Arguments { get; init; } = new();
    public string[] DependsOn      { get; init; } = Array.Empty<string>();
    public bool     IsRollbackStep { get; init; } = false;
    public string   Description    { get; init; } = string.Empty;
}

/// <summary>
/// A complete ordered plan produced by the PlanningEngine.
/// Lives in Core so ExecutionEngine (Automation) can reference it.
/// </summary>
public record WorkflowPlan
{
    public string         PlanId              { get; init; } = Guid.NewGuid().ToString();
    public string         IntentName          { get; init; } = string.Empty;
    public string         GoalDescription     { get; init; } = string.Empty;
    public RiskLevel      Risk                { get; init; } = RiskLevel.Low;
    public List<TaskStep> Steps               { get; init; } = new();
    public List<TaskStep> RollbackSteps       { get; init; } = new();
    public string[]       RequiredPermissions { get; init; } = Array.Empty<string>();
    public TimeSpan       EstimatedDuration   { get; init; } = TimeSpan.FromSeconds(5);
    public bool           RequiresConfirmation{ get; init; } = false;
}
