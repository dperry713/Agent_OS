using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using AetherShell.AI.Intent;
using AetherShell.Core.Interfaces;

namespace AetherShell.AI.Planning;

/// <summary>
/// Converts a classified intent into an ordered WorkflowPlan with risk analysis
/// and rollback capability.
/// </summary>
public class PlanningEngine
{
    private readonly IMemoryService _memory;

    public PlanningEngine(IMemoryService memory)
    {
        _memory = memory;
    }

    public async Task<WorkflowPlan> CreatePlanAsync(IntentResult intent, string rawCommand)
    {
        // Check memory for patterns from prior runs of this intent
        var history = await _memory.GetWorkflowHistoryAsync(10);

        return intent.IntentName switch
        {
            "LaunchApplication"  => PlanLaunchApp(intent),
            "ExecuteCommand"     => PlanExecuteCommand(intent),
            "ReadFile"           => PlanReadFile(intent),
            "WriteFile"          => PlanWriteFile(intent),
            "ListDirectory"      => PlanListDirectory(intent),
            "OrganizeFiles"      => PlanOrganizeFiles(intent),
            "AnalyzeScreen"      => PlanAnalyzeScreen(intent),
            "GetRegistryValue"   => PlanGetRegistry(intent),
            "SetRegistryValue"   => PlanSetRegistry(intent),
            "RunWorkflow"        => PlanRunWorkflow(intent, rawCommand),
            "SystemDiagnostics"  => PlanDiagnostics(intent),
            "BuildProject"       => PlanBuildProject(intent),
            "RunTests"           => PlanRunTests(intent),
            "GitOperation"       => PlanGitOperation(intent),
            "OpenUrl"            => PlanOpenUrl(intent),
            "QueryMemory"        => PlanQueryMemory(intent),
            "ListPlugins"        => PlanListPlugins(intent),
            "Help"               => PlanHelp(intent),
            "SearchWeb"          => PlanSearchWeb(intent, rawCommand),
            _                    => PlanGeneric(intent, rawCommand)
        };
    }

    // ── Plan Builders ─────────────────────────────────────────────────────────

    private WorkflowPlan PlanLaunchApp(IntentResult intent)
    {
        var app = intent.ExtractedEntities.GetValueOrDefault("appName", "notepad");
        return new WorkflowPlan
        {
            IntentName      = intent.IntentName,
            GoalDescription = $"Launch application: {app}",
            Risk            = RiskLevel.Low,
            Steps           = new List<TaskStep>
            {
                new() { AgentName = "SystemAgent", ToolName = "launch_app",
                        Arguments = new() { ["appName"] = app },
                        Description = $"Launch {app}" }
            }
        };
    }

    private WorkflowPlan PlanExecuteCommand(IntentResult intent)
    {
        var cmd = intent.ExtractedEntities.GetValueOrDefault("command", "");
        return new WorkflowPlan
        {
            IntentName      = intent.IntentName,
            GoalDescription = $"Execute: {cmd}",
            Risk            = RiskLevel.Medium,
            Steps           = new List<TaskStep>
            {
                new() { AgentName = "AutomationAgent", ToolName = "execute_command",
                        Arguments = new() { ["command"] = cmd },
                        Description = $"Run command: {cmd}" }
            }
        };
    }

    private WorkflowPlan PlanReadFile(IntentResult intent)
    {
        var path = intent.ExtractedEntities.GetValueOrDefault("path", "");
        return new WorkflowPlan
        {
            IntentName = intent.IntentName, GoalDescription = $"Read: {path}",
            Risk = RiskLevel.Low,
            Steps = new List<TaskStep>
            {
                new() { AgentName = "FileAgent", ToolName = "read_file",
                        Arguments = new() { ["path"] = path }, Description = $"Read file: {path}" }
            }
        };
    }

    private WorkflowPlan PlanWriteFile(IntentResult intent)
    {
        var path    = intent.ExtractedEntities.GetValueOrDefault("path", "");
        var content = intent.ExtractedEntities.GetValueOrDefault("content", "");
        return new WorkflowPlan
        {
            IntentName = intent.IntentName, GoalDescription = $"Write to: {path}",
            Risk = RiskLevel.Medium, RequiresConfirmation = false,
            Steps = new List<TaskStep>
            {
                new() { AgentName = "FileAgent", ToolName = "write_file",
                        Arguments = new() { ["path"] = path, ["content"] = content },
                        Description = $"Write file: {path}" }
            },
            RollbackSteps = new List<TaskStep>
            {
                new() { AgentName = "FileAgent", ToolName = "execute_command",
                        Arguments = new() { ["command"] = $"del \"{path}\"" },
                        IsRollbackStep = true, Description = "Rollback: delete written file" }
            }
        };
    }

    private WorkflowPlan PlanListDirectory(IntentResult intent)
    {
        var path = intent.ExtractedEntities.GetValueOrDefault("path",
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile));
        return new WorkflowPlan
        {
            IntentName = intent.IntentName, GoalDescription = $"List: {path}",
            Risk = RiskLevel.Low,
            Steps = new List<TaskStep>
            {
                new() { AgentName = "FileAgent", ToolName = "list_directory",
                        Arguments = new() { ["path"] = path }, Description = $"List {path}" }
            }
        };
    }

    private WorkflowPlan PlanOrganizeFiles(IntentResult intent)
    {
        var path = intent.ExtractedEntities.GetValueOrDefault("path",
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile) + @"\Downloads");
        return new WorkflowPlan
        {
            IntentName = intent.IntentName, GoalDescription = $"Organize folder: {path}",
            Risk = RiskLevel.High, RequiresConfirmation = true,
            RequiredPermissions = new[] { "FileWrite" },
            EstimatedDuration = TimeSpan.FromSeconds(10),
            Steps = new List<TaskStep>
            {
                new() { AgentName = "FileAgent", ToolName = "list_directory",
                        Arguments = new() { ["path"] = path }, Description = "Analyze folder contents" },
                new() { AgentName = "FileAgent", ToolName = "organize_files",
                        Arguments = new() { ["path"] = path }, DependsOn = new[]{"0"},
                        Description = "Classify and move files into subfolders" },
                new() { AgentName = "MemoryAgent", ToolName = "store_pattern",
                        Arguments = new() { ["key"] = "FileOrganization", ["value"] = path },
                        DependsOn = new[]{"1"}, Description = "Store organization pattern in memory" }
            }
        };
    }

    private WorkflowPlan PlanAnalyzeScreen(IntentResult intent)
        => new() { IntentName = intent.IntentName, GoalDescription = "OCR screen analysis",
            Risk = RiskLevel.Low, Steps = new List<TaskStep>
            { new() { AgentName = "VisionAgent", ToolName = "analyze_screen", Description = "Capture and OCR screen" } } };

    private WorkflowPlan PlanGetRegistry(IntentResult intent)
    {
        var e = intent.ExtractedEntities;
        return new WorkflowPlan
        {
            IntentName = intent.IntentName, GoalDescription = "Read registry value",
            Risk = RiskLevel.Low, Steps = new List<TaskStep>
            {
                new() { AgentName = "SystemAgent", ToolName = "get_registry_value",
                        Arguments = new() {
                            ["hive"] = e.GetValueOrDefault("hive","CurrentUser"),
                            ["keyPath"] = e.GetValueOrDefault("keyPath",""),
                            ["valueName"] = e.GetValueOrDefault("valueName","") },
                        Description = "Query registry" }
            }
        };
    }

    private WorkflowPlan PlanSetRegistry(IntentResult intent)
    {
        var e = intent.ExtractedEntities;
        return new WorkflowPlan
        {
            IntentName = intent.IntentName, GoalDescription = "Write registry value",
            Risk = RiskLevel.High, RequiredPermissions = new[] { "RegistryWrite" },
            Steps = new List<TaskStep>
            {
                new() { AgentName = "SystemAgent", ToolName = "set_registry_value",
                        Arguments = new() {
                            ["hive"] = e.GetValueOrDefault("hive","CurrentUser"),
                            ["keyPath"] = e.GetValueOrDefault("keyPath",""),
                            ["valueName"] = e.GetValueOrDefault("valueName",""),
                            ["valueData"] = e.GetValueOrDefault("valueData","") },
                        Description = "Set registry key" }
            }
        };
    }

    private WorkflowPlan PlanRunWorkflow(IntentResult intent, string raw)
        => new() { IntentName = intent.IntentName, GoalDescription = $"Execute workflow: {raw}",
            Risk = RiskLevel.Medium, Steps = new List<TaskStep>
            { new() { AgentName = "AutomationAgent", ToolName = "run_workflow",
                      Arguments = new() { ["definition"] = raw }, Description = "Run workflow" } } };

    private WorkflowPlan PlanDiagnostics(IntentResult intent)
    {
        var steps = new List<TaskStep>
        {
            new() { AgentName = "SystemAgent", ToolName = "get_system_metrics", Description = "Collect CPU/Memory/Disk" },
            new() { AgentName = "SystemAgent", ToolName = "execute_command",
                    Arguments = new() { ["command"] = "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10" },
                    DependsOn = new[]{"0"}, Description = "Top processes by CPU" }
        };
        return new WorkflowPlan { IntentName = intent.IntentName, GoalDescription = "System diagnostics",
            Risk = RiskLevel.Low, Steps = steps, EstimatedDuration = TimeSpan.FromSeconds(3) };
    }

    private WorkflowPlan PlanBuildProject(IntentResult intent)
        => new() { IntentName = intent.IntentName, GoalDescription = "Build the AetherShell solution",
            Risk = RiskLevel.Low, EstimatedDuration = TimeSpan.FromSeconds(20),
            Steps = new List<TaskStep>
            {
                new() { AgentName = "CodingAgent", ToolName = "execute_command",
                        Arguments = new() { ["command"] = "dotnet build" }, Description = "dotnet build" }
            }};

    private WorkflowPlan PlanRunTests(IntentResult intent)
        => new() { IntentName = intent.IntentName, GoalDescription = "Run unit tests",
            Risk = RiskLevel.Low, EstimatedDuration = TimeSpan.FromSeconds(30),
            Steps = new List<TaskStep>
            {
                new() { AgentName = "CodingAgent", ToolName = "execute_command",
                        Arguments = new() { ["command"] = "dotnet test" }, Description = "dotnet test" }
            }};

    private WorkflowPlan PlanGitOperation(IntentResult intent)
    {
        var args = intent.ExtractedEntities.GetValueOrDefault("gitArgs", "status");
        return new() { IntentName = intent.IntentName, GoalDescription = $"git {args}",
            Risk = args.Contains("push") || args.Contains("commit") ? RiskLevel.Medium : RiskLevel.Low,
            Steps = new List<TaskStep>
            {
                new() { AgentName = "CodingAgent", ToolName = "git",
                        Arguments = new() { ["args"] = args }, Description = $"git {args}" }
            }};
    }

    private WorkflowPlan PlanOpenUrl(IntentResult intent)
    {
        var url = intent.ExtractedEntities.GetValueOrDefault("url", "https://google.com");
        return new() { IntentName = intent.IntentName, GoalDescription = $"Open URL: {url}",
            Risk = RiskLevel.Low, Steps = new List<TaskStep>
            { new() { AgentName = "BrowserAgent", ToolName = "open_url",
                      Arguments = new() { ["url"] = url }, Description = $"Navigate to {url}" } } };
    }

    private WorkflowPlan PlanQueryMemory(IntentResult intent)
        => new() { IntentName = intent.IntentName, GoalDescription = "Query conversation/workflow memory",
            Risk = RiskLevel.Low, Steps = new List<TaskStep>
            { new() { AgentName = "MemoryAgent", ToolName = "query_history",
                      Arguments = new() { ["limit"] = "10" }, Description = "Retrieve history" } } };

    private WorkflowPlan PlanListPlugins(IntentResult intent)
        => new() { IntentName = intent.IntentName, GoalDescription = "List active plugins/modules",
            Risk = RiskLevel.Low, Steps = new List<TaskStep>
            { new() { AgentName = "SystemAgent", ToolName = "list_plugins", Description = "List plugins" } } };

    private WorkflowPlan PlanHelp(IntentResult intent)
        => new() { IntentName = intent.IntentName, GoalDescription = "Show help and capabilities",
            Risk = RiskLevel.Low, Steps = new List<TaskStep>
            { new() { AgentName = "SystemAgent", ToolName = "show_help", Description = "Show help" } } };

    private WorkflowPlan PlanSearchWeb(IntentResult intent, string raw)
    {
        var query = raw;
        foreach (var kw in new[]{"search ","google ","look up ","find online ","research "})
            if (query.StartsWith(kw, StringComparison.OrdinalIgnoreCase))
                { query = query.Substring(kw.Length); break; }
        query = query.Trim();
        return new() { IntentName = intent.IntentName, GoalDescription = $"Search: {query}",
            Risk = RiskLevel.Low, Steps = new List<TaskStep>
            { new() { AgentName = "BrowserAgent", ToolName = "open_url",
                      Arguments = new() { ["url"] = $"https://www.google.com/search?q={Uri.EscapeDataString(query)}" },
                      Description = $"Search for: {query}" } } };
    }

    private WorkflowPlan PlanGeneric(IntentResult intent, string raw)
        => new() { IntentName = "Generic", GoalDescription = raw,
            Risk = RiskLevel.Low, Steps = new List<TaskStep>
            { new() { AgentName = intent.SuggestedAgent, ToolName = "respond",
                      Arguments = new() { ["query"] = raw }, Description = "Handle generic query" } } };
}
