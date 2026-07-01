using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Logging;

namespace AetherShell.Core.Services;

/// <summary>
/// SQLite-backed memory service: persistent knowledge store, conversation history,
/// workflow outcomes, and audit log.
/// </summary>
public class MemoryService : IMemoryService
{
    private readonly ILogger<MemoryService> _logger;
    private readonly string _dbPath;

    public MemoryService(ILogger<MemoryService> logger)
    {
        _logger = logger;
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var dir = Path.Combine(appData, "AetherShell");
        Directory.CreateDirectory(dir);
        _dbPath = Path.Combine(dir, "memory.db");
        InitializeDatabase();
    }

    // ── Schema Bootstrap ──────────────────────────────────────────────────────

    private void InitializeDatabase()
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                collection TEXT NOT NULL DEFAULT 'default',
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                workflow_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS workflow_outcomes (
                workflow_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                success INTEGER NOT NULL,
                summary TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                payload TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """;
        cmd.ExecuteNonQuery();
    }

    // ── Key-Value Store ───────────────────────────────────────────────────────

    public Task StoreAsync(string key, object data, string collection = "default")
    {
        var json = JsonSerializer.Serialize(data);
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT INTO knowledge (id, collection, key, value)
            VALUES ($id, $col, $key, $val)
            ON CONFLICT(id) DO UPDATE SET value = $val;
            """;
        cmd.Parameters.AddWithValue("$id", $"{collection}:{key}");
        cmd.Parameters.AddWithValue("$col", collection);
        cmd.Parameters.AddWithValue("$key", key);
        cmd.Parameters.AddWithValue("$val", json);
        cmd.ExecuteNonQuery();
        return Task.CompletedTask;
    }

    public Task<T?> RetrieveAsync<T>(string key, string collection = "default")
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT value FROM knowledge WHERE id = $id;";
        cmd.Parameters.AddWithValue("$id", $"{collection}:{key}");
        var raw = cmd.ExecuteScalar() as string;
        if (raw is null) return Task.FromResult<T?>(default);
        return Task.FromResult<T?>(JsonSerializer.Deserialize<T>(raw));
    }

    public Task<IEnumerable<T>> SearchAsync<T>(string query, int limit = 10)
    {
        // Simple substring search on serialized value
        var results = new List<T>();
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT value FROM knowledge WHERE value LIKE $q LIMIT $lim;";
        cmd.Parameters.AddWithValue("$q", $"%{query}%");
        cmd.Parameters.AddWithValue("$lim", limit);
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            try
            {
                var item = JsonSerializer.Deserialize<T>(reader.GetString(0));
                if (item is not null) results.Add(item);
            }
            catch { /* skip malformed rows */ }
        }
        return Task.FromResult<IEnumerable<T>>(results);
    }

    // ── Conversation History ──────────────────────────────────────────────────

    public Task StoreConversationAsync(string query, string response, string? workflowId = null)
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT INTO conversations (id, query, response, workflow_id)
            VALUES ($id, $q, $r, $wid);
            """;
        cmd.Parameters.AddWithValue("$id", Guid.NewGuid().ToString());
        cmd.Parameters.AddWithValue("$q", query);
        cmd.Parameters.AddWithValue("$r", response);
        cmd.Parameters.AddWithValue("$wid", workflowId ?? (object)DBNull.Value);
        cmd.ExecuteNonQuery();
        return Task.CompletedTask;
    }

    public Task<IEnumerable<ConversationEntry>> GetConversationHistoryAsync(int limit = 20)
    {
        var entries = new List<ConversationEntry>();
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, query, response, created_at, workflow_id FROM conversations ORDER BY created_at DESC LIMIT $lim;";
        cmd.Parameters.AddWithValue("$lim", limit);
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
            entries.Add(new ConversationEntry(
                reader.GetString(0),
                reader.GetString(1),
                reader.GetString(2),
                reader.GetDateTime(3),
                reader.IsDBNull(4) ? null : reader.GetString(4)));
        return Task.FromResult<IEnumerable<ConversationEntry>>(entries);
    }

    // ── Workflow Outcomes ─────────────────────────────────────────────────────

    public Task StoreOutcomeAsync(string workflowId, string workflowName, bool success, string summary)
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT INTO workflow_outcomes (workflow_id, name, success, summary)
            VALUES ($wid, $name, $ok, $sum)
            ON CONFLICT(workflow_id) DO UPDATE SET success=$ok, summary=$sum;
            """;
        cmd.Parameters.AddWithValue("$wid", workflowId);
        cmd.Parameters.AddWithValue("$name", workflowName);
        cmd.Parameters.AddWithValue("$ok", success ? 1 : 0);
        cmd.Parameters.AddWithValue("$sum", summary);
        cmd.ExecuteNonQuery();
        return Task.CompletedTask;
    }

    public Task<IEnumerable<WorkflowOutcome>> GetWorkflowHistoryAsync(int limit = 20)
    {
        var list = new List<WorkflowOutcome>();
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT workflow_id, name, success, summary, created_at FROM workflow_outcomes ORDER BY created_at DESC LIMIT $lim;";
        cmd.Parameters.AddWithValue("$lim", limit);
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
            list.Add(new WorkflowOutcome(
                reader.GetString(0),
                reader.GetString(1),
                reader.GetInt32(2) == 1,
                reader.GetString(3),
                reader.GetDateTime(4)));
        return Task.FromResult<IEnumerable<WorkflowOutcome>>(list);
    }

    // ── Helper ────────────────────────────────────────────────────────────────

    public void AppendAuditLog(string eventType, string source, string? payload = null)
    {
        try
        {
            using var conn = Open();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "INSERT INTO audit_log (id, event_type, source, payload) VALUES ($id, $et, $src, $pay);";
            cmd.Parameters.AddWithValue("$id", Guid.NewGuid().ToString());
            cmd.Parameters.AddWithValue("$et", eventType);
            cmd.Parameters.AddWithValue("$src", source);
            cmd.Parameters.AddWithValue("$pay", payload ?? (object)DBNull.Value);
            cmd.ExecuteNonQuery();
        }
        catch (Exception ex)
        {
            _logger.LogWarning("Audit log write failed: {Err}", ex.Message);
        }
    }

    private SqliteConnection Open()
    {
        var conn = new SqliteConnection($"Data Source={_dbPath}");
        conn.Open();
        return conn;
    }
}