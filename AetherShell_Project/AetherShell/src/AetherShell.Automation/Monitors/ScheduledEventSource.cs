using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AetherShell.Core.Events;
using AetherShell.Core.Interfaces;
using Microsoft.Extensions.Logging;

namespace AetherShell.Automation.Monitors;

public record ScheduleEntry(string Id, string Description, TimeSpan Interval, DateTime LastFired);

/// <summary>
/// Fires ScheduledTickEvent for each registered schedule based on their interval.
/// Simple interval-based scheduler (no cron parsing dependency).
/// </summary>
public class ScheduledEventSource : IDisposable
{
    private readonly ILogger<ScheduledEventSource> _logger;
    private readonly IEventBus                     _bus;
    private readonly List<ScheduleEntry>            _schedules = new();
    private Timer? _timer;

    public ScheduledEventSource(ILogger<ScheduledEventSource> logger, IEventBus bus)
    {
        _logger = logger;
        _bus    = bus;
    }

    public void Register(string id, string description, TimeSpan interval)
    {
        _schedules.Add(new ScheduleEntry(id, description, interval, DateTime.MinValue));
        _logger.LogInformation("[Scheduler] Registered '{Id}' every {Sec}s", id, interval.TotalSeconds);
    }

    public void Start()
    {
        _timer = new Timer(_ => _ = TickAsync(), null, TimeSpan.FromSeconds(10), TimeSpan.FromSeconds(10));
    }

    private async Task TickAsync()
    {
        var now = DateTime.UtcNow;
        for (int i = 0; i < _schedules.Count; i++)
        {
            var entry = _schedules[i];
            if ((now - entry.LastFired) >= entry.Interval)
            {
                _schedules[i] = entry with { LastFired = now };
                await _bus.PublishAsync(new ScheduledTickEvent(entry.Id, now));
                _logger.LogDebug("[Scheduler] Fired: {Id}", entry.Id);
            }
        }
    }

    public void Dispose() => _timer?.Dispose();
}
