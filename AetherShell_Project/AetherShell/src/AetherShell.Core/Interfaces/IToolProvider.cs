using System.Collections.Generic;
using System.Threading.Tasks;

namespace AetherShell.Core.Interfaces;

public record ToolResult(bool Success, string Output, string? ErrorMessage = null);

/// <summary>
/// A pluggable tool provider that executes named tools.
/// </summary>
public interface IToolProvider
{
    string[] SupportedTools { get; }
    Task<ToolResult> ExecuteAsync(string tool, Dictionary<string, string> args);
}
