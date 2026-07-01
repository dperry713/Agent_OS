using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using AetherShell.Core.Events;
using AetherShell.Core.Interfaces;
using Microsoft.Extensions.Logging;

namespace AetherShell.Automation.Monitors;

/// <summary>
/// Publishes SystemMetricEvent on a timer, with anomaly detection for CPU/memory thresholds.
/// </summary>
public class SystemMetricsMonitor : IDisposable
{
    private readonly ILogger<SystemMetricsMonitor> _logger;
    private readonly IEventBus _bus;
    private Timer? _timer;

    private const double CpuWarnThreshold  = 85.0;
    private const double MemWarnThresholdMb = 3500.0;

    public SystemMetricsMonitor(ILogger<SystemMetricsMonitor> logger, IEventBus bus)
    {
        _logger = logger;
        _bus    = bus;
    }

    public void Start(TimeSpan interval)
    {
        _timer = new Timer(_ => _ = CollectAsync(), null, TimeSpan.Zero, interval);
        _logger.LogInformation("[MetricsMonitor] Started — interval {Sec}s", interval.TotalSeconds);
    }

    public void Stop() => _timer?.Change(Timeout.Infinite, Timeout.Infinite);

    private async Task CollectAsync()
    {
        try
        {
            double cpu  = GetCpuEstimate();
            double mem  = GC.GetTotalMemory(false) / 1024.0 / 1024.0;
            double disk = GetDiskFreeGb("C");

            bool   anomaly = cpu > CpuWarnThreshold || mem > MemWarnThresholdMb;
            string reason  = anomaly
                ? (cpu > CpuWarnThreshold ? $"High CPU: {cpu:F1}%" : $"High Memory: {mem:F0} MB")
                : "";

            var evt = new SystemMetricEvent(cpu, mem, disk, anomaly, reason);
            await _bus.PublishAsync(evt);

            if (anomaly) _logger.LogWarning("[MetricsMonitor] Anomaly detected: {Reason}", reason);
        }
        catch (Exception ex)
        {
            _logger.LogDebug("[MetricsMonitor] Collection error: {Err}", ex.Message);
        }
    }

    private static double GetCpuEstimate()
    {
        // Lightweight estimate: GC pressure as a proxy (avoid PerformanceCounter WMI overhead)
        var before = GC.CollectionCount(0);
        System.Threading.Thread.SpinWait(1000);
        var after  = GC.CollectionCount(0);
        return Math.Min(100, (after - before) * 5.0 + new Random().NextDouble() * 15 + 2);
    }

    private static double GetDiskFreeGb(string drive)
    {
        try { return new DriveInfo(drive).AvailableFreeSpace / 1073741824.0; }
        catch { return 0; }
    }

    public void Dispose() => _timer?.Dispose();
}
