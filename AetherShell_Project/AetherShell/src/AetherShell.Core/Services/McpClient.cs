using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;
using Microsoft.Extensions.Logging;

namespace AetherShell.Core.Services;

public class McpClient : IDisposable
{
    private readonly ILogger<McpClient> _logger;
    private Process? _agentOsProcess;
    private StreamWriter? _stdin;
    private StreamReader? _stdout;
    private int _requestId = 0;
    private readonly SemaphoreSlim _sendLock = new SemaphoreSlim(1, 1);

    public McpClient(ILogger<McpClient> logger)
    {
        _logger = logger;
    }

    public void Start()
    {
        try
        {
            var appDir = AppDomain.CurrentDomain.BaseDirectory;
            var agentOsPath = Path.Combine(appDir, "AgentOS.exe");
            if (!File.Exists(agentOsPath))
            {
                _logger.LogWarning("McpClient: AgentOS.exe not found at {Path}", agentOsPath);
                return;
            }

            _logger.LogInformation("McpClient: Starting AgentOS MCP Server from {Path}...", agentOsPath);

            _agentOsProcess = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = agentOsPath,
                    UseShellExecute = false,
                    RedirectStandardInput = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                }
            };

            _agentOsProcess.Start();
            _stdin = _agentOsProcess.StandardInput;
            _stdout = _agentOsProcess.StandardOutput;

            // Log stderr outputs
            Task.Run(async () =>
            {
                try
                {
                    while (_agentOsProcess != null && !_agentOsProcess.HasExited)
                    {
                        var errLine = await _agentOsProcess.StandardError.ReadLineAsync();
                        if (errLine != null)
                        {
                            _logger.LogWarning("AgentOS Stderr: {Msg}", errLine);
                        }
                    }
                }
                catch { }
            });

            // Initialize handshake
            Task.Run(async () =>
            {
                try
                {
                    await CallToolInternalAsync("initialize", "{}");
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "McpClient initialize handshake failed");
                }
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start AgentOS MCP process");
        }
    }

    public async Task<string> CallToolAsync(string toolName, string argumentsJson)
    {
        return await CallToolInternalAsync("tools/call", $"{{\"name\":\"{toolName}\",\"arguments\":{argumentsJson}}}");
    }

    private async Task<string> CallToolInternalAsync(string method, string paramsJson)
    {
        if (_stdin == null || _stdout == null)
        {
            return "Error: MCP client is not connected to AgentOS.";
        }

        int id = Interlocked.Increment(ref _requestId);
        var requestNode = new JsonObject
        {
            ["jsonrpc"] = "2.0",
            ["id"] = id,
            ["method"] = method,
            ["params"] = JsonNode.Parse(paramsJson)
        };

        await _sendLock.WaitAsync();
        try
        {
            string reqStr = JsonSerializer.Serialize(requestNode);
            await _stdin.WriteLineAsync(reqStr);
            await _stdin.FlushAsync();

            while (true)
            {
                string? respLine = await _stdout.ReadLineAsync();
                if (respLine == null)
                {
                    return "Error: AgentOS MCP stream disconnected.";
                }

                try
                {
                    var responseNode = JsonNode.Parse(respLine);
                    if (responseNode == null) continue;

                    var respId = responseNode["id"]?.GetValue<int>();
                    if (respId == id)
                    {
                        var error = responseNode["error"];
                        if (error != null)
                        {
                            return $"MCP Error: {error["message"]?.GetValue<string>()}";
                        }

                        if (method == "initialize")
                        {
                            return "Initialized";
                        }

                        var contentArray = responseNode["result"]?["content"] as JsonArray;
                        if (contentArray != null && contentArray.Count > 0)
                        {
                            return contentArray[0]?["text"]?.GetValue<string>() ?? "Success";
                        }

                        return responseNode["result"]?.ToString() ?? "Success";
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogWarning("McpClient parse error: {Msg}", ex.Message);
                }
            }
        }
        finally
        {
            _sendLock.Release();
        }
    }

    public void Dispose()
    {
        try
        {
            if (_agentOsProcess != null && !_agentOsProcess.HasExited)
            {
                _agentOsProcess.Kill();
            }
            _agentOsProcess?.Dispose();
        }
        catch { }
    }
}
