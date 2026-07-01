using Microsoft.SemanticKernel;
using AetherShell.Core.Interfaces;

namespace AetherShell.AI.Orchestrator;

/// <summary>
/// Initial Semantic Kernel setup and agent registration.
/// </summary>
public class SemanticKernelBootstrap
{
    public static Kernel CreateKernel()
    {
        var builder = Kernel.CreateBuilder();
        // Add plugins, memory, connectors here
        // Example: builder.AddOpenAIChatCompletion(...);
        return builder.Build();
    }
}