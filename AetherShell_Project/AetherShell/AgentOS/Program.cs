using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading.Tasks;
using Microsoft.Win32;

namespace AgentOS;

class Program
{
    static async Task Main(string[] args)
    {
        while (true)
        {
            var line = await Console.In.ReadLineAsync();
            if (line == null) break;

            try
            {
                var request = JsonNode.Parse(line);
                if (request == null) continue;

                var id = request["id"]?.GetValue<long>();
                var method = request["method"]?.GetValue<string>();

                if (method == "initialize")
                {
                    var response = new
                    {
                        jsonrpc = "2.0",
                        id = id,
                        result = new
                        {
                            protocolVersion = "2024-11-05",
                            capabilities = new { },
                            serverInfo = new
                            {
                                name = "AgentOS-MCP",
                                version = "1.0.0"
                            }
                        }
                    };
                    Console.Out.WriteLine(JsonSerializer.Serialize(response));
                    Console.Out.Flush();
                }
                else if (method == "tools/list")
                {
                    var response = new
                    {
                        jsonrpc = "2.0",
                        id = id,
                        result = new
                        {
                            tools = new object[]
                            {
                                new
                                {
                                    name = "launch_app",
                                    description = "Launches any system application (e.g. chrome, notepad, calculator, cmd, powershell).",
                                    inputSchema = new
                                    {
                                        type = "object",
                                        properties = new
                                        {
                                            appName = new { type = "string" },
                                            arguments = new { type = "string" }
                                        },
                                        required = new[] { "appName" }
                                    }
                                },
                                new
                                {
                                    name = "execute_command",
                                    description = "Executes a system shell command or PowerShell script.",
                                    inputSchema = new
                                    {
                                        type = "object",
                                        properties = new
                                        {
                                            command = new { type = "string" }
                                        },
                                        required = new[] { "command" }
                                    }
                                },
                                new
                                {
                                    name = "read_file",
                                    description = "Reads text contents from a file on disk.",
                                    inputSchema = new
                                    {
                                        type = "object",
                                        properties = new
                                        {
                                            path = new { type = "string" }
                                        },
                                        required = new[] { "path" }
                                    }
                                },
                                new
                                {
                                    name = "write_file",
                                    description = "Writes text contents to a file on disk.",
                                    inputSchema = new
                                    {
                                        type = "object",
                                        properties = new
                                        {
                                            path = new { type = "string" },
                                            content = new { type = "string" }
                                        },
                                        required = new[] { "path", "content" }
                                    }
                                },
                                new
                                {
                                    name = "list_directory",
                                    description = "Lists files and subdirectories inside a directory path.",
                                    inputSchema = new
                                    {
                                        type = "object",
                                        properties = new
                                        {
                                            path = new { type = "string" }
                                        },
                                        required = new[] { "path" }
                                    }
                                },
                                new
                                {
                                    name = "get_registry_value",
                                    description = "Retrieves a registry key value.",
                                    inputSchema = new
                                    {
                                        type = "object",
                                        properties = new
                                        {
                                            hive = new { type = "string", @enum = new[] { "CurrentUser", "LocalMachine" } },
                                            keyPath = new { type = "string" },
                                            valueName = new { type = "string" }
                                        },
                                        required = new[] { "hive", "keyPath", "valueName" }
                                    }
                                },
                                new
                                {
                                    name = "set_registry_value",
                                    description = "Sets a registry key value.",
                                    inputSchema = new
                                    {
                                        type = "object",
                                        properties = new
                                        {
                                            hive = new { type = "string", @enum = new[] { "CurrentUser", "LocalMachine" } },
                                            keyPath = new { type = "string" },
                                            valueName = new { type = "string" },
                                            valueData = new { type = "string" }
                                        },
                                        required = new[] { "hive", "keyPath", "valueName", "valueData" }
                                    }
                                }
                            }
                        }
                    };
                    Console.Out.WriteLine(JsonSerializer.Serialize(response));
                    Console.Out.Flush();
                }
                else if (method == "tools/call")
                {
                    var toolName = request["params"]?["name"]?.GetValue<string>();
                    var arguments = request["params"]?["arguments"];
                    string resultText = "";

                    if (toolName == "launch_app")
                    {
                        var appName = arguments?["appName"]?.GetValue<string>();
                        var appArgs = arguments?["arguments"]?.GetValue<string>() ?? "";
                        resultText = LaunchApplication(appName, appArgs);
                    }
                    else if (toolName == "execute_command")
                    {
                        var cmd = arguments?["command"]?.GetValue<string>();
                        resultText = ExecuteShellCommand(cmd);
                    }
                    else if (toolName == "read_file")
                    {
                        var path = arguments?["path"]?.GetValue<string>();
                        resultText = ReadFileSystemFile(path);
                    }
                    else if (toolName == "write_file")
                    {
                        var path = arguments?["path"]?.GetValue<string>();
                        var content = arguments?["content"]?.GetValue<string>() ?? "";
                        resultText = WriteFileSystemFile(path, content);
                    }
                    else if (toolName == "list_directory")
                    {
                        var path = arguments?["path"]?.GetValue<string>();
                        resultText = ListFileSystemDirectory(path);
                    }
                    else if (toolName == "get_registry_value")
                    {
                        var hive = arguments?["hive"]?.GetValue<string>();
                        var keyPath = arguments?["keyPath"]?.GetValue<string>();
                        var valName = arguments?["valueName"]?.GetValue<string>();
                        resultText = GetRegistryControlValue(hive, keyPath, valName);
                    }
                    else if (toolName == "set_registry_value")
                    {
                        var hive = arguments?["hive"]?.GetValue<string>();
                        var keyPath = arguments?["keyPath"]?.GetValue<string>();
                        var valName = arguments?["valueName"]?.GetValue<string>();
                        var valData = arguments?["valueData"]?.GetValue<string>();
                        resultText = SetRegistryControlValue(hive, keyPath, valName, valData);
                    }
                    else
                    {
                        resultText = $"Error: Tool '{toolName}' not found.";
                    }

                    var response = new
                    {
                        jsonrpc = "2.0",
                        id = id,
                        result = new
                        {
                            content = new[]
                            {
                                new
                                {
                                    type = "text",
                                    text = resultText
                                }
                            }
                        }
                    };
                    Console.Out.WriteLine(JsonSerializer.Serialize(response));
                    Console.Out.Flush();
                }
            }
            catch (Exception ex)
            {
                var errorResponse = new
                {
                    jsonrpc = "2.0",
                    error = new
                    {
                        code = -32603,
                        message = ex.Message
                    }
                };
                Console.Out.WriteLine(JsonSerializer.Serialize(errorResponse));
                Console.Out.Flush();
            }
        }
    }

    private static string LaunchApplication(string appName, string arguments)
    {
        if (string.IsNullOrWhiteSpace(appName)) return "Error: appName is empty.";

        var t = appName.ToLowerInvariant();
        string filename = appName;

        if (t.Contains("chrome")) filename = "chrome.exe";
        else if (t.Contains("notepad")) filename = "notepad.exe";
        else if (t.Contains("calc") || t.Contains("calculator")) filename = "calc.exe";

        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = filename,
                Arguments = arguments,
                UseShellExecute = true
            });
            return $"AgentOS MCP: Successfully launched {filename} with arguments '{arguments}'.";
        }
        catch (Exception ex)
        {
            return $"AgentOS MCP Error: Failed to launch application '{filename}': {ex.Message}";
        }
    }

    private static string ExecuteShellCommand(string command)
    {
        if (string.IsNullOrWhiteSpace(command)) return "Error: command is empty.";

        try
        {
            var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "powershell.exe",
                    Arguments = $"-NoProfile -ExecutionPolicy Bypass -Command \"{command}\"",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                }
            };
            process.Start();
            string output = process.StandardOutput.ReadToEnd();
            string error = process.StandardError.ReadToEnd();
            process.WaitForExit();

            if (!string.IsNullOrEmpty(error))
            {
                return $"AgentOS MCP command failed: {error}";
            }
            return $"AgentOS MCP command output:\n{output}";
        }
        catch (Exception ex)
        {
            return $"AgentOS MCP Error executing command: {ex.Message}";
        }
    }

    private static string ReadFileSystemFile(string? path)
    {
        if (string.IsNullOrWhiteSpace(path)) return "Error: path is empty.";
        try
        {
            if (!File.Exists(path)) return $"Error: File '{path}' does not exist.";
            string content = File.ReadAllText(path);
            return $"[File Content: {path}]\n{content}";
        }
        catch (Exception ex)
        {
            return $"Error reading file '{path}': {ex.Message}";
        }
    }

    private static string WriteFileSystemFile(string? path, string content)
    {
        if (string.IsNullOrWhiteSpace(path)) return "Error: path is empty.";
        try
        {
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }
            File.WriteAllText(path, content);
            return $"Success: Wrote content to file '{path}' successfully.";
        }
        catch (Exception ex)
        {
            return $"Error writing file '{path}': {ex.Message}";
        }
    }

    private static string ListFileSystemDirectory(string? path)
    {
        if (string.IsNullOrWhiteSpace(path)) return "Error: path is empty.";
        try
        {
            if (!Directory.Exists(path)) return $"Error: Directory '{path}' does not exist.";
            var files = Directory.GetFiles(path);
            var dirs = Directory.GetDirectories(path);

            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"[Directory Contents: {path}]");
            foreach (var d in dirs) sb.AppendLine($"  [DIR]  {Path.GetFileName(d)}");
            foreach (var f in files) sb.AppendLine($"  [FILE] {Path.GetFileName(f)} ({new FileInfo(f).Length} bytes)");
            return sb.ToString();
        }
        catch (Exception ex)
        {
            return $"Error listing directory '{path}': {ex.Message}";
        }
    }

    private static string GetRegistryControlValue(string? hive, string? keyPath, string? valueName)
    {
        if (string.IsNullOrWhiteSpace(hive) || string.IsNullOrWhiteSpace(keyPath) || string.IsNullOrWhiteSpace(valueName))
            return "Error: hive, keyPath, and valueName must be provided.";

        try
        {
            RegistryKey? baseKey = hive.Equals("LocalMachine", StringComparison.OrdinalIgnoreCase) ? Registry.LocalMachine : Registry.CurrentUser;
            using var subKey = baseKey.OpenSubKey(keyPath);
            if (subKey == null) return $"Error: Registry key '{hive}\\{keyPath}' not found.";

            var val = subKey.GetValue(valueName);
            if (val == null) return $"Error: Registry value '{valueName}' not found under '{hive}\\{keyPath}'.";

            return $"Registry [{hive}\\{keyPath}\\{valueName}] = {val} (Type: {subKey.GetValueKind(valueName)})";
        }
        catch (Exception ex)
        {
            return $"Registry Error: {ex.Message}";
        }
    }

    private static string SetRegistryControlValue(string? hive, string? keyPath, string? valueName, string? valueData)
    {
        if (string.IsNullOrWhiteSpace(hive) || string.IsNullOrWhiteSpace(keyPath) || string.IsNullOrWhiteSpace(valueName) || valueData == null)
            return "Error: hive, keyPath, valueName, and valueData must be provided.";

        try
        {
            RegistryKey? baseKey = hive.Equals("LocalMachine", StringComparison.OrdinalIgnoreCase) ? Registry.LocalMachine : Registry.CurrentUser;
            using var subKey = baseKey.CreateSubKey(keyPath);
            if (subKey == null) return $"Error: Failed to create/open Registry key '{hive}\\{keyPath}'.";

            subKey.SetValue(valueName, valueData);
            return $"Registry Success: Set [{hive}\\{keyPath}\\{valueName}] to '{valueData}'.";
        }
        catch (Exception ex)
        {
            return $"Registry Error setting value: {ex.Message}";
        }
    }
}
