using System.Collections.Generic;

namespace AetherShell.AI.Intent;

/// <summary>
/// Describes a recognizable user intent with matching patterns and target agent.
/// </summary>
public record IntentDefinition(
    string   Name,
    string   Description,
    string   AgentName,
    string[] Keywords,
    string[] ExamplePhrases
);

/// <summary>
/// Central catalog of every supported intent in the AetherShell platform.
/// </summary>
public static class IntentRegistry
{
    public static IReadOnlyList<IntentDefinition> All { get; } = new List<IntentDefinition>
    {
        new("LaunchApplication",    "Open or start a system application",          "SystemAgent",
            new[]{"open","start","launch","run app"},
            new[]{"open chrome","launch notepad","start calculator"}),

        new("ExecuteCommand",       "Run a shell or PowerShell command",            "AutomationAgent",
            new[]{"shell","cmd","powershell","execute","run command"},
            new[]{"shell dir","powershell get-process","run command ipconfig"}),

        new("ReadFile",             "Read file contents from disk",                 "FileAgent",
            new[]{"read","cat","view file","show file"},
            new[]{"read C:\\file.txt","view C:\\notes.txt"}),

        new("WriteFile",            "Write or create a file on disk",               "FileAgent",
            new[]{"write","create file","save file"},
            new[]{"write C:\\file.txt hello world"}),

        new("ListDirectory",        "List files inside a directory",                "FileAgent",
            new[]{"ls","dir","list directory","list files","show folder"},
            new[]{"ls C:\\","dir C:\\Users","list files in downloads"}),

        new("OrganizeFiles",        "Organize or sort files in a folder",           "FileAgent",
            new[]{"organize","sort files","clean folder","arrange"},
            new[]{"organize downloads","sort desktop files","clean downloads folder"}),

        new("AnalyzeScreen",        "Run OCR or visual analysis of the screen",     "VisionAgent",
            new[]{"analyze","screen","vision","ocr","scan desktop","capture"},
            new[]{"analyze screen","run ocr","capture desktop"}),

        new("GetRegistryValue",     "Read a Windows registry value",                "SystemAgent",
            new[]{"get reg","registry get","read registry"},
            new[]{"get reg CurrentUser Console FaceName"}),

        new("SetRegistryValue",     "Write a Windows registry value",               "SystemAgent",
            new[]{"set reg","registry set","write registry"},
            new[]{"set reg CurrentUser Console FaceName Consolas"}),

        new("RunWorkflow",          "Execute an automation workflow",               "AutomationAgent",
            new[]{"workflow","automation","run workflow","automate"},
            new[]{"run clean build workflow","automate deployment"}),

        new("SystemDiagnostics",    "Check system health and metrics",              "SystemAgent",
            new[]{"diagnose","health","status","metrics","check system","system info"},
            new[]{"check system health","show diagnostics","system status"}),

        new("SearchWeb",            "Search the web for information",               "ResearchAgent",
            new[]{"search","google","look up","find online","research"},
            new[]{"search for dotnet documentation","google latest news"}),

        new("GitOperation",         "Run a git command",                            "CodingAgent",
            new[]{"git","commit","push","pull","clone","git status","git log"},
            new[]{"git status","git commit -m fix","git push"}),

        new("BuildProject",         "Build or compile the project",                 "CodingAgent",
            new[]{"build","compile","dotnet build","rebuild"},
            new[]{"build the project","compile solution","dotnet build"}),

        new("RunTests",             "Execute unit or integration tests",            "CodingAgent",
            new[]{"test","run tests","dotnet test","unit test"},
            new[]{"run tests","dotnet test","run unit tests"}),

        new("OpenUrl",              "Open a URL in the browser",                    "BrowserAgent",
            new[]{"open url","browse","navigate to","go to","http","www"},
            new[]{"open https://google.com","browse to github.com"}),

        new("VoiceDictation",       "Listen via microphone and dictate",            "VoiceAgent",
            new[]{"listen","dictate","voice","microphone","speak"},
            new[]{"listen for voice input","start dictation"}),

        new("QueryMemory",          "Retrieve past conversation or workflow memory","MemoryAgent",
            new[]{"remember","recall","history","what did i","memory","past conversations"},
            new[]{"what did I do last time","show workflow history","recall last command"}),

        new("ListPlugins",          "Show active modules and plugins",              "SystemAgent",
            new[]{"plugins","modules","list plugins","extensions"},
            new[]{"show active plugins","list modules"}),

        new("Help",                 "Show capabilities and usage help",             "SystemAgent",
            new[]{"help","capabilities","what can you","commands","usage"},
            new[]{"help","what can you do","show commands"}),
    };
}
