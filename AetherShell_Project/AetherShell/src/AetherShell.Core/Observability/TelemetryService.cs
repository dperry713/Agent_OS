using System.Diagnostics;
using OpenTelemetry.Trace;

namespace AetherShell.Core.Observability;

/// <summary>
/// Centralized telemetry for the entire platform.
/// </summary>
public class TelemetryService
{
    public ActivitySource ActivitySource { get; } = new("AetherShell");

    public void RecordMetric(string name, double value)
    {
        // OpenTelemetry metrics
    }
}