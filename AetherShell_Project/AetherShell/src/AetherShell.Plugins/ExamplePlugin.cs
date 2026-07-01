using System.Threading.Tasks;
using Microsoft.SemanticKernel;
using AetherShell.Core.Interfaces;

namespace AetherShell.Plugins;

/// <summary>
/// Example plugin demonstrating extension model.
/// </summary>
public class ExamplePlugin : IPlugin
{
    public string Name => "ExamplePlugin";
    public string Version => "1.0.0";

    public Task InitializeAsync()
    {
        return Task.CompletedTask;
    }

    [KernelFunction("get_system_info")]
    public string GetSystemInfo()
    {
        return "AetherShell v0.3 - Running on Windows with full AI capabilities.";
    }
}