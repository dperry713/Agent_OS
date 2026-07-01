using System.Collections.Generic;
using System.Threading.Tasks;

namespace AetherShell.Core.Interfaces;

/// <summary>
/// Extended memory interface with persistent conversation, outcome, and audit log support.
/// </summary>
public interface IMemoryService
{
    // ── Key-Value Store ───────────────────────────────────────────────────────
    Task StoreAsync(string key, object data, string collection = "default");
    Task<T?> RetrieveAsync<T>(string key, string collection = "default");
    Task<IEnumerable<T>> SearchAsync<T>(string query, int limit = 10);

    // ── Conversation History ──────────────────────────────────────────────────
    Task StoreConversationAsync(string query, string response, string? workflowId = null);
    Task<IEnumerable<ConversationEntry>> GetConversationHistoryAsync(int limit = 20);

    // ── Workflow Outcomes ─────────────────────────────────────────────────────
    Task StoreOutcomeAsync(string workflowId, string workflowName, bool success, string summary);
    Task<IEnumerable<WorkflowOutcome>> GetWorkflowHistoryAsync(int limit = 20);
}

public record ConversationEntry(string Id, string Query, string Response, System.DateTime At, string? WorkflowId);
public record WorkflowOutcome(string WorkflowId, string Name, bool Success, string Summary, System.DateTime At);