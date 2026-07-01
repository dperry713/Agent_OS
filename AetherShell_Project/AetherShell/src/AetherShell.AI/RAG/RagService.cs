using System.Threading.Tasks;
using AetherShell.Core.Interfaces;

namespace AetherShell.AI.RAG;

/// <summary>
/// Retrieval-Augmented Generation service.
/// </summary>
public class RagService
{
    private readonly IMemoryService _memory;

    public RagService(IMemoryService memory)
    {
        _memory = memory;
    }

    public async Task<string> QueryAsync(string userQuery)
    {
        // Retrieve context + generate response via Kernel
        var context = await _memory.SearchAsync<string>(userQuery);
        return $"AI Response to '{userQuery}' with context.";
    }
}