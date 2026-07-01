using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using AetherShell.Core.Events;
using AetherShell.Core.Interfaces;
using Microsoft.Extensions.Logging;

namespace AetherShell.Automation.Monitors;

/// <summary>
/// Watches filesystem paths for changes and publishes FileChangedEvent to the event bus.
/// </summary>
public class FileSystemMonitor : IDisposable
{
    private readonly ILogger<FileSystemMonitor> _logger;
    private readonly IEventBus                  _bus;
    private readonly FileSystemWatcher          _watcher;

    public FileSystemMonitor(ILogger<FileSystemMonitor> logger, IEventBus bus, string watchPath)
    {
        _logger = logger;
        _bus    = bus;

        if (!Directory.Exists(watchPath))
            Directory.CreateDirectory(watchPath);

        _watcher = new FileSystemWatcher(watchPath)
        {
            IncludeSubdirectories = true,
            EnableRaisingEvents   = false,
            NotifyFilter          = NotifyFilters.FileName | NotifyFilters.Size | NotifyFilters.LastWrite
        };

        _watcher.Created += OnChanged;
        _watcher.Changed += OnChanged;
        _watcher.Deleted += OnChanged;
        _watcher.Renamed += OnRenamed;
    }

    public void Start() => _watcher.EnableRaisingEvents = true;
    public void Stop()  => _watcher.EnableRaisingEvents = false;

    private void OnChanged(object sender, FileSystemEventArgs e)
    {
        var size = e.ChangeType != WatcherChangeTypes.Deleted && File.Exists(e.FullPath)
            ? new FileInfo(e.FullPath).Length : 0;
        _ = _bus.PublishAsync(new FileChangedEvent(e.FullPath, e.ChangeType.ToString(), size));
        _logger.LogDebug("[FSMonitor] {Type}: {Path}", e.ChangeType, e.FullPath);
    }

    private void OnRenamed(object sender, RenamedEventArgs e)
        => _ = _bus.PublishAsync(new FileChangedEvent(e.FullPath, "Renamed"));

    public void Dispose() => _watcher.Dispose();
}
