using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AetherShell.Core.Interfaces;

namespace AetherShell.AI.Intent;

/// <summary>
/// Classifies natural language commands into named intents with extracted entities.
/// Uses ordered keyword/pattern matching with context memory enrichment.
/// </summary>
public class IntentClassifier
{
    private readonly IMemoryService _memory;

    public IntentClassifier(IMemoryService memory)
    {
        _memory = memory;
    }

    public async Task<IntentResult> ClassifyAsync(string command)
    {
        if (string.IsNullOrWhiteSpace(command))
            return new IntentResult { IntentName = "Unknown", Confidence = 0 };

        var q   = command.ToLowerInvariant().Trim();
        var best = FindBestMatch(q, command);

        // Enrich from memory: if we've done this intent before, bump confidence slightly
        var history = await _memory.GetWorkflowHistoryAsync(5);
        bool hasHistory = history.Any(h => h.Name.Contains(best.IntentName, StringComparison.OrdinalIgnoreCase));
        double boostedConfidence = hasHistory ? Math.Min(1.0, best.Confidence + 0.05) : best.Confidence;

        return best with { Confidence = boostedConfidence };
    }

    private IntentResult FindBestMatch(string q, string original)
    {
        IntentResult? top = null;
        double topScore = 0;

        foreach (var intent in IntentRegistry.All)
        {
            double score = ScoreIntent(q, intent);
            if (score > topScore)
            {
                topScore = score;
                top = new IntentResult
                {
                    IntentName        = intent.Name,
                    Confidence        = score,
                    SuggestedAgent    = intent.AgentName,
                    GoalDescription   = intent.Description,
                    ExtractedEntities = ExtractEntities(q, original, intent.Name)
                };
            }
        }

        return top ?? new IntentResult { IntentName = "Unknown", Confidence = 0, SuggestedAgent = "SystemAgent" };
    }

    private static double ScoreIntent(string q, IntentDefinition intent)
    {
        double score = 0;

        // Keyword matching (weighted by length — longer phrases are more specific)
        foreach (var kw in intent.Keywords)
        {
            if (q.Contains(kw))
                score += 0.3 + (kw.Split(' ').Length * 0.1); // multi-word bonus
        }

        // Example phrase matching (higher weight)
        foreach (var ex in intent.ExamplePhrases)
        {
            var exLower = ex.ToLowerInvariant();
            if (q == exLower)           { score += 1.0; break; }  // exact
            if (q.StartsWith(exLower))  { score += 0.8; break; }  // prefix
            if (q.Contains(exLower))    { score += 0.5; break; }  // contains
        }

        return Math.Min(score, 1.0);
    }

    private static Dictionary<string, string> ExtractEntities(string q, string original, string intentName)
    {
        var entities = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        switch (intentName)
        {
            case "LaunchApplication":
                ExtractAfterKeywords(original, q, new[]{"open ","start ","launch ","run app "}, entities, "appName");
                break;
            case "ExecuteCommand":
                ExtractAfterKeywords(original, q, new[]{"shell ","cmd ","powershell ","run command ","execute "}, entities, "command");
                break;
            case "ReadFile":
                ExtractAfterKeywords(original, q, new[]{"read ","cat ","view file ","show file "}, entities, "path");
                break;
            case "WriteFile":
                ExtractAfterKeywordsTwo(original, q, new[]{"write ","create file ","save file "}, entities, "path", "content");
                break;
            case "ListDirectory":
                ExtractAfterKeywords(original, q, new[]{"ls ","dir ","list files in ","show folder "}, entities, "path");
                break;
            case "OrganizeFiles":
                ExtractAfterKeywords(original, q, new[]{"organize ","sort files in ","clean folder ","arrange "}, entities, "path");
                if (!entities.ContainsKey("path"))
                    entities["path"] = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile) + @"\Downloads";
                break;
            case "GetRegistryValue":
                ExtractRegistryArgs(q, entities, expectValue: false);
                break;
            case "SetRegistryValue":
                ExtractRegistryArgs(q, entities, expectValue: true);
                break;
            case "OpenUrl":
                ExtractAfterKeywords(original, q, new[]{"open url ","browse to ","navigate to ","go to ","open "}, entities, "url");
                if (!entities.ContainsKey("url") && (q.Contains("http") || q.Contains("www")))
                {
                    var parts = original.Split(' ');
                    var url = parts.FirstOrDefault(p => p.StartsWith("http", StringComparison.OrdinalIgnoreCase)
                                                     || p.StartsWith("www", StringComparison.OrdinalIgnoreCase));
                    if (url != null) entities["url"] = url;
                }
                break;
            case "GitOperation":
                ExtractAfterKeywords(original, q, new[]{"git "}, entities, "gitArgs");
                break;
        }

        return entities;
    }

    private static void ExtractAfterKeywords(string original, string q, string[] prefixes, Dictionary<string, string> entities, string key)
    {
        foreach (var prefix in prefixes)
        {
            int idx = q.IndexOf(prefix, StringComparison.Ordinal);
            if (idx >= 0)
            {
                entities[key] = original.Substring(idx + prefix.Length).Trim();
                return;
            }
        }
    }

    private static void ExtractAfterKeywordsTwo(string original, string q, string[] prefixes, Dictionary<string, string> entities, string pathKey, string contentKey)
    {
        foreach (var prefix in prefixes)
        {
            int idx = q.IndexOf(prefix, StringComparison.Ordinal);
            if (idx >= 0)
            {
                var remainder = original.Substring(idx + prefix.Length).Trim();
                int space = remainder.IndexOf(' ');
                if (space > 0)
                {
                    entities[pathKey]    = remainder.Substring(0, space);
                    entities[contentKey] = remainder.Substring(space + 1);
                }
                else
                {
                    entities[pathKey] = remainder;
                }
                return;
            }
        }
    }

    private static void ExtractRegistryArgs(string q, Dictionary<string, string> entities, bool expectValue)
    {
        // Format: "get reg <hive> <keyPath> <valueName>" or "set reg <hive> <keyPath> <valueName> <valueData>"
        var tokens = q.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        int offset = tokens.Length > 0 && (tokens[0] == "get" || tokens[0] == "set") ? 2 : 0;
        if (tokens.Length > offset)     entities["hive"]      = tokens[offset];
        if (tokens.Length > offset + 1) entities["keyPath"]   = tokens[offset + 1];
        if (tokens.Length > offset + 2) entities["valueName"] = tokens[offset + 2];
        if (expectValue && tokens.Length > offset + 3)
            entities["valueData"] = string.Join(' ', tokens[(offset + 3)..]);
    }
}
