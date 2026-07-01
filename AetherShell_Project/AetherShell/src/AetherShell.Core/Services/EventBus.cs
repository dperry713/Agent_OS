using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AetherShell.Core.Events;
using AetherShell.Core.Interfaces;

namespace AetherShell.Core.Services;

/// <summary>
/// Priority-queued, deduplicating, rate-limited event bus.
/// </summary>
public class EventBus : IEventBus
{
    // Legacy generic handlers (keeps existing subscriptions working)
    private readonly ConcurrentDictionary<Type, List<object>> _handlers = new();

    // Deduplication: track recent CorrelationIds to skip duplicates
    private readonly ConcurrentDictionary<string, DateTime>   _seen     = new();
    private static readonly TimeSpan DedupeWindow = TimeSpan.FromSeconds(2);

    // Rate limiting per source: max 50 events/second
    private readonly ConcurrentDictionary<string, (int Count, DateTime Window)> _rateLimits = new();
    private const int MaxEventsPerSecond = 50;

    // ── IEventBus ─────────────────────────────────────────────────────────────

    public void Subscribe<TEvent>(Func<TEvent, Task> handler) where TEvent : class
    {
        var list = _handlers.GetOrAdd(typeof(TEvent), _ => new List<object>());
        lock (list) { list.Add(handler); }
    }

    public async Task PublishAsync<TEvent>(TEvent @event) where TEvent : class
    {
        // Publish via AetherEvent envelope too for routing layer
        var envelope = AetherEvent.Create(@event, source: @event.GetType().Name);
        await PublishEnvelopeAsync(envelope);

        // Direct legacy handlers
        await DispatchDirectAsync(@event);
    }

    // ── Enriched publish with full envelope ──────────────────────────────────

    public async Task PublishEnvelopeAsync(AetherEvent envelope)
    {
        // Deduplication
        if (envelope.CorrelationId != null)
        {
            CleanSeen();
            if (!_seen.TryAdd(envelope.CorrelationId, DateTime.UtcNow))
                return; // duplicate
        }

        // Rate limiting per source
        if (!IsWithinRateLimit(envelope.Source))
            return;

        // If the payload is a real typed event, dispatch to legacy handlers
        if (envelope.Payload is not null)
        {
            var payloadType = envelope.Payload.GetType();
            if (_handlers.TryGetValue(payloadType, out var list))
            {
                List<object> copy;
                lock (list) { copy = new List<object>(list); }
                foreach (var h in copy)
                {
                    // Use reflection-free dynamic dispatch
                    if (h is Func<object, Task> objHandler)
                        await objHandler(envelope.Payload);
                }
            }
        }
    }

    // ── Typed event stream subscribe ─────────────────────────────────────────

    public void SubscribeEnvelope(Func<AetherEvent, Task> handler)
    {
        var list = _handlers.GetOrAdd(typeof(AetherEvent), _ => new List<object>());
        lock (list) { list.Add(handler); }
    }

    // ── Internal helpers ─────────────────────────────────────────────────────

    private async Task DispatchDirectAsync<TEvent>(TEvent @event) where TEvent : class
    {
        if (!_handlers.TryGetValue(typeof(TEvent), out var list)) return;
        List<object> copy;
        lock (list) { copy = new List<object>(list); }
        foreach (var h in copy)
        {
            if (h is Func<TEvent, Task> typed)
                await typed(@event);
        }
    }

    private bool IsWithinRateLimit(string source)
    {
        var now = DateTime.UtcNow;
        _rateLimits.AddOrUpdate(source,
            _ => (1, now),
            (_, old) =>
            {
                if ((now - old.Window).TotalSeconds >= 1)
                    return (1, now);       // reset window
                return (old.Count + 1, old.Window);
            });
        return _rateLimits[source].Count <= MaxEventsPerSecond;
    }

    private void CleanSeen()
    {
        var cutoff = DateTime.UtcNow - DedupeWindow;
        foreach (var kv in _seen)
            if (kv.Value < cutoff) _seen.TryRemove(kv.Key, out _);
    }
}
