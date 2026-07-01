using System.Threading.Tasks;

namespace AetherShell.Core.Interfaces;

/// <summary>
/// Trigger system for automation.
/// </summary>
public interface IWorkflowTrigger
{
    Task<bool> CheckConditionAsync();
    event EventHandler Triggered;
}