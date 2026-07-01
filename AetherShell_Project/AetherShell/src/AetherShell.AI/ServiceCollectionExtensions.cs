using System.Collections.Generic;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.SemanticKernel;
using AetherShell.AI.Orchestrator;
using AetherShell.AI.Agents;
using AetherShell.AI.Intent;
using AetherShell.AI.Planning;
using AetherShell.AI.RAG;
using AetherShell.Core.Interfaces;

namespace AetherShell.AI;

/// <summary>
/// Extension methods for configuring AetherShell AI services.
/// </summary>
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddAetherShellAI(this IServiceCollection services)
    {
        services.AddSingleton<Kernel>(sp => SemanticKernelBootstrap.CreateKernel());
        services.AddSingleton<RagService>();

        // Intent + Planning pipeline
        services.AddSingleton<IntentClassifier>();
        services.AddSingleton<PlanningEngine>();

        // Specialized agents
        services.AddSingleton<SystemAgent>();
        services.AddSingleton<FileAgent>();
        services.AddSingleton<AutomationAgent>();
        services.AddSingleton<ResearchAgent>();
        services.AddSingleton<CodingAgent>();
        services.AddSingleton<VoiceAgent>();
        services.AddSingleton<VisionAgent>();
        services.AddSingleton<SecurityAgent>();
        services.AddSingleton<MemoryAgent>();
        services.AddSingleton<BrowserAgent>();

        // Register all as ISpecializedAgent
        services.AddSingleton<IEnumerable<ISpecializedAgent>>(sp => new ISpecializedAgent[]
        {
            sp.GetRequiredService<SystemAgent>(),
            sp.GetRequiredService<FileAgent>(),
            sp.GetRequiredService<AutomationAgent>(),
            sp.GetRequiredService<ResearchAgent>(),
            sp.GetRequiredService<CodingAgent>(),
            sp.GetRequiredService<VoiceAgent>(),
            sp.GetRequiredService<VisionAgent>(),
            sp.GetRequiredService<SecurityAgent>(),
            sp.GetRequiredService<MemoryAgent>(),
            sp.GetRequiredService<BrowserAgent>(),
        });

        // Orchestration
        services.AddSingleton<AgentOrchestrator>();
        services.AddSingleton<ResultProcessor>();
        services.AddSingleton<SupervisorAgent>();
        return services;
    }
}
