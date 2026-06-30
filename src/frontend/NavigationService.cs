using System;
using System.Collections.ObjectModel;
using System.Linq;
using ReactiveUI;

namespace AgentOS.Frontend
{
    public class NavigationService : ReactiveObject
    {
        // List of module keys and display names
        public ObservableCollection<ModuleInfo> Modules { get; } = new ObservableCollection<ModuleInfo>
        {
            new ModuleInfo("Settings", "Settings"),
            new ModuleInfo("UserProfiles", "User Profiles"),
            new ModuleInfo("TaskQueue", "Task Queue"),
            new ModuleInfo("MemoryExplorer", "Memory Explorer"),
            new ModuleInfo("KnowledgeGraph", "Knowledge Graph"),
            new ModuleInfo("WorkflowDesigner", "Workflow Designer"),
            new ModuleInfo("AutomationStudio", "Automation Studio"),
            new ModuleInfo("IntegratedIDE", "Integrated IDE"),
            new ModuleInfo("Terminal", "Terminal"),
            new ModuleInfo("Git", "Git"),
            new ModuleInfo("PackageManager", "Package Manager"),
            new ModuleInfo("PluginMarketplace", "Plugin Marketplace"),
            new ModuleInfo("ModelManager", "Model Manager"),
            new ModuleInfo("PromptLibrary", "Prompt Library"),
            new ModuleInfo("SecurityCenter", "Security Center"),
            new ModuleInfo("PolicyCenter", "Policy Center"),
            new ModuleInfo("SecretsVault", "Secrets Vault"),
            new ModuleInfo("ContainerManager", "Container Manager"),
            new ModuleInfo("DatabaseExplorer", "Database Explorer"),
            new ModuleInfo("APIExplorer", "API Explorer"),
            new ModuleInfo("Monitoring", "Monitoring"),
            new ModuleInfo("Analytics", "Analytics"),
            new ModuleInfo("Notifications", "Notifications"),
            new ModuleInfo("Extensions", "Extensions"),
            new ModuleInfo("Documentation", "Documentation"),
            new ModuleInfo("Dashboard", "Dashboard"),
            new ModuleInfo("Projects", "Projects"),
            new ModuleInfo("Workspace", "Workspace"),
            new ModuleInfo("AgentControlCenter", "Agent Control Center")
        };

        private string _currentModule = "Settings";
        public string CurrentModule
        {
            get => _currentModule;
            set => this.RaiseAndSetIfChanged(ref _currentModule, value);
        }

        public void NavigateTo(string moduleKey)
        {
            if (Modules.Any(m => m.Key == moduleKey))
                CurrentModule = moduleKey;
        }
    }

    public record ModuleInfo(string Key, string DisplayName);
}
