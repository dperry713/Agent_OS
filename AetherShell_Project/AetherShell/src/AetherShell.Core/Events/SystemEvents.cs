using System;

namespace AetherShell.Core.Events;

// ── System / Shell ──────────────────────────────────────────────────────────
public record FileChangedEvent(string Path, string ChangeType, long SizeBytes = 0);
public record RegistryChangedEvent(string Hive, string KeyPath);
public record UserCommandEvent(string Command, string Source = "CommandPalette");
public record ApplicationLaunchedEvent(string AppName, int Pid);
public record ScheduledTickEvent(string ScheduleId, DateTime FireTime);

// ── System Metrics ───────────────────────────────────────────────────────────
public record SystemMetricEvent(
    double CpuPercent,
    double MemoryMb,
    double DiskFreeGb,
    bool   IsAnomaly = false,
    string AnomalyReason = "");

// ── Workflow Lifecycle ────────────────────────────────────────────────────────
public record WorkflowStartedEvent(string WorkflowId, string WorkflowName);
public record WorkflowStepCompletedEvent(string WorkflowId, int StepIndex, string StepName, string Result);
public record WorkflowCompletedEvent(string WorkflowId, string WorkflowName, string Summary, TimeSpan Duration);
public record WorkflowFailedEvent(string WorkflowId, string StepName, string Error, bool RolledBack);

// ── Agent ─────────────────────────────────────────────────────────────────────
public record AgentCompletedEvent(string AgentName, string IntentName, string Result);

// ── Screen / Vision ───────────────────────────────────────────────────────────
public record ScreenAnalysisCompletedEvent(string OcrText, string[] DetectedWindows);
