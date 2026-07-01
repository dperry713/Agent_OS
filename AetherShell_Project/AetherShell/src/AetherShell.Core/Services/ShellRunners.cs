using System;
using System.Diagnostics;
using System.Text;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;

namespace AetherShell.Core.Services;

/// <summary>
/// Runs PowerShell commands in a child process and captures output.
/// </summary>
public class PowerShellRunner : IToolProvider
{
    public string[] SupportedTools => new[] { "powershell" };

    public Task<ToolResult> ExecuteAsync(string tool, System.Collections.Generic.Dictionary<string, string> args)
        => RunAsync(args.GetValueOrDefault("command", "echo ready"));

    public async Task<ToolResult> RunAsync(string command)
    {
        var psi = new ProcessStartInfo
        {
            FileName               = "powershell.exe",
            Arguments              = $"-NoProfile -NonInteractive -Command \"{command.Replace("\"", "\\\"")}\"",
            RedirectStandardOutput = true,
            RedirectStandardError  = true,
            UseShellExecute        = false,
            CreateNoWindow         = true
        };

        using var proc = new Process { StartInfo = psi };
        var sb = new StringBuilder();
        proc.OutputDataReceived += (_, e) => { if (e.Data != null) sb.AppendLine(e.Data); };
        proc.ErrorDataReceived  += (_, e) => { if (e.Data != null) sb.AppendLine($"ERR: {e.Data}"); };

        proc.Start();
        proc.BeginOutputReadLine();
        proc.BeginErrorReadLine();
        await proc.WaitForExitAsync();

        string output = sb.ToString().Trim();
        return new ToolResult(proc.ExitCode == 0, output,
            proc.ExitCode != 0 ? $"Exit code {proc.ExitCode}" : null);
    }
}

/// <summary>
/// Runs git commands in the workspace directory.
/// </summary>
public class GitRunner : IToolProvider
{
    private readonly string _workDir;
    public string[] SupportedTools => new[] { "git" };

    public GitRunner(string? workDir = null)
    {
        _workDir = workDir ?? Environment.CurrentDirectory;
    }

    public Task<ToolResult> ExecuteAsync(string tool, System.Collections.Generic.Dictionary<string, string> args)
        => RunAsync(args.GetValueOrDefault("args", "status"));

    public async Task<ToolResult> RunAsync(string gitArgs)
    {
        var psi = new ProcessStartInfo
        {
            FileName               = "git",
            Arguments              = gitArgs,
            WorkingDirectory       = _workDir,
            RedirectStandardOutput = true,
            RedirectStandardError  = true,
            UseShellExecute        = false,
            CreateNoWindow         = true
        };

        using var proc = new Process { StartInfo = psi };
        var sb = new StringBuilder();
        proc.OutputDataReceived += (_, e) => { if (e.Data != null) sb.AppendLine(e.Data); };
        proc.ErrorDataReceived  += (_, e) => { if (e.Data != null) sb.AppendLine($"ERR: {e.Data}"); };

        proc.Start();
        proc.BeginOutputReadLine();
        proc.BeginErrorReadLine();
        await proc.WaitForExitAsync();

        return new ToolResult(proc.ExitCode == 0, sb.ToString().Trim());
    }
}
