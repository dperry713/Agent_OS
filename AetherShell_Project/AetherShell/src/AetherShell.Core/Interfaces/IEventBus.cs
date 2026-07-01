using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace AetherShell.Core.Interfaces;

/// <summary>
/// Extended event bus interface with deduplication and envelope-level publishing.
/// </summary>
public interface IEventBus
{
    void Subscribe<TEvent>(Func<TEvent, Task> handler) where TEvent : class;
    Task PublishAsync<TEvent>(TEvent @event) where TEvent : class;
}