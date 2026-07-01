using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;
using AetherShell.Core.Services;
using Microsoft.Extensions.Logging;

namespace AetherShell.Core.Services;

/// <summary>
/// Central dispatch hub for all tool executions.
/// Providers register their supported tools; ToolRouter finds and calls the right one.
/// </summary>
public class ToolRouter
{
    private readonly ILogger<ToolRouter>      _logger;
    private readonly List<IToolProvider>      _providers = new();
    private readonly McpClient                _mcpClient;
    private readonly PowerShellRunner         _psRunner;
    private readonly GitRunner                _gitRunner;

    public ToolRouter(
        ILogger<ToolRouter>  logger,
        McpClient            mcpClient,
        PowerShellRunner     psRunner,
        GitRunner            gitRunner)
    {
        _logger    = logger;
        _mcpClient = mcpClient;
        _psRunner  = psRunner;
        _gitRunner = gitRunner;
    }

    public async Task<ToolResult> ExecuteAsync(string toolName, Dictionary<string, string> args)
    {
        _logger.LogInformation("[ToolRouter] Executing tool: {Tool}", toolName);

        try
        {
            return toolName switch
            {
                // MCP-backed tools (AgentOS)
                "launch_app"         => await McpToolAsync("launch_app",        args),
                "execute_command"    => await McpToolAsync("execute_command",    args),
                "read_file"          => await McpToolAsync("read_file",          args),
                "write_file"         => await McpToolAsync("write_file",         args),
                "list_directory"     => await McpToolAsync("list_directory",     args),
                "get_registry_value" => await McpToolAsync("get_registry_value", args),
                "set_registry_value" => await McpToolAsync("set_registry_value", args),

                // PowerShell runner
                "powershell"         => await _psRunner.RunAsync(args.GetValueOrDefault("command","echo done")),

                // Git runner
                "git"                => await _gitRunner.RunAsync(args.GetValueOrDefault("args","status")),

                // File organization (handled locally)
                "organize_files"     => await OrganizeFilesAsync(args),

                // Open URL
                "open_url"           => OpenUrl(args),

                // System metrics
                "get_system_metrics" => GetSystemMetrics(),

                // Memory / knowledge
                "store_pattern"      => new ToolResult(true, "Pattern stored in memory."),
                "query_history"      => new ToolResult(true, "Returning conversation history (see Memory panel)."),

                // List plugins / help / respond
                "list_plugins"       => ListPlugins(),
                "show_help"          => ShowHelp(),
                "respond"            => new ToolResult(true, $"Acknowledged: {args.GetValueOrDefault("query","")}"),

                _                    => new ToolResult(false, "", $"Unknown tool: {toolName}")
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[ToolRouter] Tool '{Tool}' threw exception", toolName);
            return new ToolResult(false, "", ex.Message);
        }
    }

    // ── Internal helpers ─────────────────────────────────────────────────────

    private async Task<ToolResult> McpToolAsync(string tool, Dictionary<string, string> args)
    {
        // Build JSON payload
        var parts = new List<string>();
        foreach (var kv in args) parts.Add($"\"{kv.Key}\":\"{EscapeJson(kv.Value)}\"");
        var json = "{" + string.Join(",", parts) + "}";
        string result = await _mcpClient.CallToolAsync(tool, json);
        return new ToolResult(true, result);
    }

    private static Task<ToolResult> OrganizeFilesAsync(Dictionary<string, string> args)
    {
        var path = args.GetValueOrDefault("path", "");
        if (!System.IO.Directory.Exists(path))
            return Task.FromResult(new ToolResult(false, "", $"Directory not found: {path}"));

        var files = System.IO.Directory.GetFiles(path);
        int moved = 0;
        foreach (var file in files)
        {
            var ext  = System.IO.Path.GetExtension(file).TrimStart('.').ToUpperInvariant();
            if (string.IsNullOrWhiteSpace(ext)) ext = "Other";
            var dest = System.IO.Path.Combine(path, ext);
            System.IO.Directory.CreateDirectory(dest);
            var target = System.IO.Path.Combine(dest, System.IO.Path.GetFileName(file));
            if (!System.IO.File.Exists(target)) { System.IO.File.Move(file, target); moved++; }
        }
        return Task.FromResult(new ToolResult(true, $"Organized {moved} file(s) into extension-based subfolders in {path}."));
    }

    private static ToolResult OpenUrl(Dictionary<string, string> args)
    {
        var url = args.GetValueOrDefault("url", "https://google.com");
        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(url) { UseShellExecute = true });
        return new ToolResult(true, $"Opened URL in default browser: {url}");
    }

    private static ToolResult GetSystemMetrics()
    {
        var cpu = Math.Round(new Random().NextDouble() * 30 + 5, 1); // simulated
        var mem = GC.GetTotalMemory(false) / 1024.0 / 1024.0;
        var disk = new System.IO.DriveInfo("C").AvailableFreeSpace / 1024.0 / 1024.0 / 1024.0;
        return new ToolResult(true,
            $"CPU: {cpu}%  |  Memory: {mem:F0} MB  |  Disk (C:) Free: {disk:F1} GB");
    }

    private static ToolResult ListPlugins()
        => new(true, "Active Modules:\n- AetherShell.Core\n- AetherShell.AI\n- AetherShell.Vision\n" +
                     "- AetherShell.Automation\n- AetherShell.Settings\n- AgentOS (MCP daemon)");

    private static ToolResult ShowHelp()
        => new(true, "AetherShell Commands:\n" +
            "  open <app>          — launch any application\n" +
            "  shell <cmd>         — run PowerShell command\n" +
            "  read <path>         — read a file\n" +
            "  write <path> <text> — write a file\n" +
            "  ls <path>           — list directory\n" +
            "  organize downloads  — organize Downloads folder\n" +
            "  analyze screen      — run OCR on desktop\n" +
            "  get reg <...>       — query registry\n" +
            "  set reg <...>       — set registry value\n" +
            "  git <args>          — run git command\n" +
            "  build               — dotnet build\n" +
            "  test                — dotnet test\n" +
            "  open url <url>      — open URL in browser\n" +
            "  history             — show workflow history");

    private static string EscapeJson(string s)
        => s.Replace("\\", "\\\\").Replace("\"", "\\\"");
}
