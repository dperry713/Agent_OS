using System;
using System.Collections.Generic;

namespace AetherShell.Core.Events;

/// <summary>
/// Priority level for event bus routing.
/// </summary>
public enum EventPriority
{
    Critical = 0,
    High     = 1,
    Normal   = 2,
    Low      = 3
}

/// <summary>
/// Normalized event envelope — every event flowing through the bus is wrapped in this.
/// </summary>
public record AetherEvent
{
    public string          EventId       { get; init; } = Guid.NewGuid().ToString();
    public DateTime        Timestamp     { get; init; } = DateTime.UtcNow;
    public string          Source        { get; init; } = "Unknown";
    public EventPriority   Priority      { get; init; } = EventPriority.Normal;
    public string?         SecurityCtx   { get; init; }
    public object?         Payload       { get; init; }
    public string?         CorrelationId { get; init; }
    public string          EventType     { get; init; } = string.Empty;
    public List<string>    Tags          { get; init; } = new();

    public static AetherEvent Create<T>(T payload, string source,
        EventPriority priority = EventPriority.Normal,
        string? correlationId = null) where T : notnull
        => new()
        {
            EventType     = typeof(T).Name,
            Source        = source,
            Priority      = priority,
            Payload       = payload,
            CorrelationId = correlationId ?? Guid.NewGuid().ToString()
        };
}
