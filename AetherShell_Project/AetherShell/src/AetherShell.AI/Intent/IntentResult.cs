using System.Collections.Generic;

namespace AetherShell.AI.Intent;

/// <summary>
/// Result of intent classification, including extracted entities and target agent.
/// </summary>
public record IntentResult
{
    public string                       IntentName        { get; init; } = "Unknown";
    public double                       Confidence        { get; init; } = 0.0;
    public Dictionary<string, string>   ExtractedEntities { get; init; } = new();
    public string                       SuggestedAgent    { get; init; } = "SystemAgent";
    public string                       GoalDescription   { get; init; } = string.Empty;
    public bool                         IsUnknown         => IntentName == "Unknown";
}
