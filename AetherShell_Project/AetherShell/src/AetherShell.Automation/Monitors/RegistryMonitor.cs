using System;
using System.Threading;
using System.Threading.Tasks;
using AetherShell.Core.Events;
using AetherShell.Core.Interfaces;
using Microsoft.Extensions.Logging;
using Microsoft.Win32;

namespace AetherShell.Automation.Monitors;

/// <summary>
/// Polls Windows registry keys for changes and publishes RegistryChangedEvent.
/// Uses polling since WaitForChangeAsync requires careful threading.
/// </summary>
public class RegistryMonitor : IDisposable
{
    private readonly ILogger<RegistryMonitor> _logger;
    private readonly IEventBus                _bus;
    private readonly string                   _hive;
    private readonly string                   _keyPath;
    private string?  _lastSnapshot;
    private Timer?   _timer;

    public RegistryMonitor(ILogger<RegistryMonitor> logger, IEventBus bus,
        string hive = "CurrentUser", string keyPath = @"Console")
    {
        _logger  = logger;
        _bus     = bus;
        _hive    = hive;
        _keyPath = keyPath;
    }

    public void Start(TimeSpan pollInterval)
    {
        _lastSnapshot = TakeSnapshot();
        _timer = new Timer(_ => _ = CheckAsync(), null, pollInterval, pollInterval);
        _logger.LogInformation("[RegMonitor] Watching {Hive}\\{Key}", _hive, _keyPath);
    }

    private async Task CheckAsync()
    {
        try
        {
            var current = TakeSnapshot();
            if (current != _lastSnapshot)
            {
                _lastSnapshot = current;
                await _bus.PublishAsync(new RegistryChangedEvent(_hive, _keyPath));
                _logger.LogInformation("[RegMonitor] Change detected in {Hive}\\{Key}", _hive, _keyPath);
            }
        }
        catch (Exception ex)
        {
            _logger.LogDebug("[RegMonitor] Poll error: {Err}", ex.Message);
        }
    }

    [System.Runtime.Versioning.SupportedOSPlatform("windows")]
    private string TakeSnapshot()
    {
        try
        {
            var root = _hive == "LocalMachine" ? Registry.LocalMachine : Registry.CurrentUser;
            using var key = root.OpenSubKey(_keyPath);
            if (key is null) return "";
            var sb = new System.Text.StringBuilder();
            foreach (var name in key.GetValueNames())
                sb.Append($"{name}={key.GetValue(name)};");
            return sb.ToString();
        }
        catch { return ""; }
    }

    public void Dispose() => _timer?.Dispose();
}
