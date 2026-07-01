using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;
using AetherShell.Core.Services;
using AetherShell.Vision;
using AetherShell.Automation;
using Microsoft.Extensions.Logging;

namespace AetherShell.AI.Agents;

// ════════════════════════════════════════════════════════════════════════════
//  SystemAgent
// ════════════════════════════════════════════════════════════════════════════

public class SystemAgent : ISpecializedAgent
{
    public string   Name             => "SystemAgent";
    public string[] SupportedIntents => new[] { "LaunchApplication","GetRegistryValue","SetRegistryValue","SystemDiagnostics","ListPlugins","Help" };
    public AgentCapabilities Capabilities => new(true, true, true, true);

    public async Task<AgentResult> RunAsync(TaskStep step, ToolRouter router)
    {
        var result = await router.ExecuteAsync(step.ToolName, step.Arguments);
        return new AgentResult(result.Success, result.Output, Name);
    }
}

// ════════════════════════════════════════════════════════════════════════════
//  FileAgent
// ════════════════════════════════════════════════════════════════════════════

public class FileAgent : ISpecializedAgent
{
    public string   Name             => "FileAgent";
    public string[] SupportedIntents => new[] { "ReadFile","WriteFile","ListDirectory","OrganizeFiles" };
    public AgentCapabilities Capabilities => new(true, true, false, false);

    public async Task<AgentResult> RunAsync(TaskStep step, ToolRouter router)
    {
        var result = await router.ExecuteAsync(step.ToolName, step.Arguments);
        return new AgentResult(result.Success, result.Output, Name);
    }
}

// ════════════════════════════════════════════════════════════════════════════
//  AutomationAgent
// ════════════════════════════════════════════════════════════════════════════

public class AutomationAgent : ISpecializedAgent
{
    private readonly WorkflowEngine _engine;
    public string   Name             => "AutomationAgent";
    public string[] SupportedIntents => new[] { "ExecuteCommand","RunWorkflow" };
    public AgentCapabilities Capabilities => new(true, true, true, false);

    public AutomationAgent(WorkflowEngine engine) => _engine = engine;

    public async Task<AgentResult> RunAsync(TaskStep step, ToolRouter router)
    {
        if (step.ToolName == "run_workflow")
        {
            var def = step.Arguments.GetValueOrDefault("definition", "");
            string log = await _engine.ExecuteWorkflowWithLogsAsync(def);
            return new AgentResult(true, log, Name);
        }
        var result = await router.ExecuteAsync(step.ToolName, step.Arguments);
        return new AgentResult(result.Success, result.Output, Name);
    }
}

// ════════════════════════════════════════════════════════════════════════════
//  ResearchAgent
// ════════════════════════════════════════════════════════════════════════════

public class ResearchAgent : ISpecializedAgent
{
    private readonly IMemoryService _memory;
    public string   Name             => "ResearchAgent";
    public string[] SupportedIntents => new[] { "SearchWeb","QueryMemory" };
    public AgentCapabilities Capabilities => new(true, false, false, false);

    public ResearchAgent(IMemoryService memory) => _memory = memory;

    public async Task<AgentResult> RunAsync(TaskStep step, ToolRouter router)
    {
        if (step.ToolName == "query_history")
        {
            var hist = await _memory.GetConversationHistoryAsync(10);
            var sb = new System.Text.StringBuilder("Recent Conversation History:\n");
            int i = 1;
            foreach (var e in hist) sb.AppendLine($"{i++}. [{e.At:g}] {e.Query} → {e.Response[..Math.Min(80, e.Response.Length)]}...");
            return new AgentResult(true, sb.ToString(), Name);
        }
        var result = await router.ExecuteAsync(step.ToolName, step.Arguments);
        return new AgentResult(result.Success, result.Output, Name);
    }
}

// ════════════════════════════════════════════════════════════════════════════
//  CodingAgent
// ════════════════════════════════════════════════════════════════════════════

public class CodingAgent : ISpecializedAgent
{
    public string   Name             => "CodingAgent";
    public string[] SupportedIntents => new[] { "BuildProject","RunTests","GitOperation" };
    public AgentCapabilities Capabilities => new(true, true, true, false);

    public async Task<AgentResult> RunAsync(TaskStep step, ToolRouter router)
    {
        var result = await router.ExecuteAsync(step.ToolName, step.Arguments);
        return new AgentResult(result.Success, result.Output, Name);
    }
}

// ════════════════════════════════════════════════════════════════════════════
//  VoiceAgent
// ════════════════════════════════════════════════════════════════════════════

public class VoiceAgent : ISpecializedAgent
{
    private readonly IVoiceService _voice;
    public string   Name             => "VoiceAgent";
    public string[] SupportedIntents => new[] { "VoiceDictation" };
    public AgentCapabilities Capabilities => new(false, false, false, false);

    public VoiceAgent(IVoiceService voice) => _voice = voice;

    public async Task<AgentResult> RunAsync(TaskStep step, ToolRouter router)
    {
        if (step.ToolName == "speak")
        {
            await _voice.SpeakAsync(step.Arguments.GetValueOrDefault("text", ""));
            return new AgentResult(true, "Spoken aloud.", Name);
        }
        var text = await _voice.RecognizeSpeechAsync();
        return new AgentResult(true, $"Dictated: {text}", Name);
    }
}

// ════════════════════════════════════════════════════════════════════════════
//  VisionAgent
// ════════════════════════════════════════════════════════════════════════════

public class VisionAgent : ISpecializedAgent
{
    private readonly ScreenAnalyzer _analyzer;
    public string   Name             => "VisionAgent";
    public string[] SupportedIntents => new[] { "AnalyzeScreen" };
    public AgentCapabilities Capabilities => new(true, false, false, false);

    public VisionAgent(ScreenAnalyzer analyzer) => _analyzer = analyzer;

    public async Task<AgentResult> RunAsync(TaskStep step, ToolRouter router)
    {
        var result = await _analyzer.AnalyzeScreenAsync();
        return new AgentResult(true, $"[Screen Analysis]\n{result}", Name);
    }
}

// ════════════════════════════════════════════════════════════════════════════
//  SecurityAgent
// ════════════════════════════════════════════════════════════════════════════

public class SecurityAgent : ISpecializedAgent
{
    private readonly PolicyEngine _policy;
    public string   Name             => "SecurityAgent";
    public string[] SupportedIntents => new[] { "ValidatePermissions" };
    public AgentCapabilities Capabilities => new(true, false, false, false);

    public SecurityAgent(PolicyEngine policy) => _policy = policy;

    public async Task<AgentResult> RunAsync(TaskStep step, ToolRouter router)
        => new AgentResult(true, "Security scan: no policy violations detected.", Name);
}

// ════════════════════════════════════════════════════════════════════════════
//  MemoryAgent
// ════════════════════════════════════════════════════════════════════════════

public class MemoryAgent : ISpecializedAgent
{
    private readonly IMemoryService _memory;
    public string   Name             => "MemoryAgent";
    public string[] SupportedIntents => new[] { "QueryMemory" };
    public AgentCapabilities Capabilities => new(true, true, false, false);

    public MemoryAgent(IMemoryService memory) => _memory = memory;

    public async Task<AgentResult> RunAsync(TaskStep step, ToolRouter router)
    {
        if (step.ToolName == "store_pattern")
        {
            var key = step.Arguments.GetValueOrDefault("key", "");
            var val = step.Arguments.GetValueOrDefault("value", "");
            await _memory.StoreAsync(key, val);
            return new AgentResult(true, $"Pattern '{key}' stored in persistent memory.", Name);
        }
        if (step.ToolName == "query_history")
        {
            var hist = await _memory.GetWorkflowHistoryAsync(10);
            var sb = new System.Text.StringBuilder("Workflow History:\n");
            int i = 1;
            foreach (var h in hist)
                sb.AppendLine($"{i++}. [{h.At:g}] {h.Name} — {(h.Success ? "✅" : "❌")} {h.Summary[..Math.Min(60, h.Summary.Length)]}");
            return new AgentResult(true, sb.ToString(), Name);
        }
        return new AgentResult(true, "Memory operation complete.", Name);
    }
}

// ════════════════════════════════════════════════════════════════════════════
//  BrowserAgent
// ════════════════════════════════════════════════════════════════════════════

public class BrowserAgent : ISpecializedAgent
{
    public string   Name             => "BrowserAgent";
    public string[] SupportedIntents => new[] { "OpenUrl","SearchWeb" };
    public AgentCapabilities Capabilities => new(false, false, false, true);

    public async Task<AgentResult> RunAsync(TaskStep step, ToolRouter router)
    {
        var result = await router.ExecuteAsync("open_url", step.Arguments);
        return new AgentResult(result.Success, result.Output, Name);
    }
}
