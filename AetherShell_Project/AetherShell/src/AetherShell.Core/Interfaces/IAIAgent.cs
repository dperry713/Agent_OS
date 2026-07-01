using System.Threading.Tasks;

namespace AetherShell.Core.Interfaces;

public class AgentExecutionContext
{
    public string Query { get; }
    public string Response { get; set; } = string.Empty;

    public AgentExecutionContext(string query)
    {
        Query = query;
    }
}

/// <summary>
/// Base AI agent contract.
/// </summary>
public interface IAIAgent
{
    string Name { get; }
    Task ExecuteAsync(object context);
}