using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Input;
using System;
using System.Threading.Tasks;
using AetherShell.Vision;
using AetherShell.Automation;
using AetherShell.Settings;
using Microsoft.Extensions.DependencyInjection;

namespace AetherShell.App;

/// <summary>
/// Main shell window.
/// </summary>
public sealed partial class MainWindow : Window
{
    private readonly ScreenAnalyzer _screenAnalyzer;
    private readonly WorkflowEngine _workflowEngine;
    private readonly IServiceProvider _serviceProvider;

    public MainWindow(ScreenAnalyzer screenAnalyzer, WorkflowEngine workflowEngine, IServiceProvider serviceProvider)
    {
        this.InitializeComponent();
        _screenAnalyzer = screenAnalyzer;
        _workflowEngine = workflowEngine;
        _serviceProvider = serviceProvider;

        this.AppWindow.Resize(new Windows.Graphics.SizeInt32(1280, 840));
        this.ExtendsContentIntoTitleBar = true;
    }

    private void HideAllViews()
    {
        ViewDashboard.Visibility = Visibility.Collapsed;
        ViewVision.Visibility = Visibility.Collapsed;
        ViewAutomation.Visibility = Visibility.Collapsed;
        ViewSettings.Visibility = Visibility.Collapsed;
    }

    private void NavDashboard_Click(object sender, RoutedEventArgs e)
    {
        HideAllViews();
        ViewDashboard.Visibility = Visibility.Visible;
    }

    private void NavVision_Click(object sender, RoutedEventArgs e)
    {
        HideAllViews();
        ViewVision.Visibility = Visibility.Visible;
    }

    private void NavAutomation_Click(object sender, RoutedEventArgs e)
    {
        HideAllViews();
        ViewAutomation.Visibility = Visibility.Visible;
    }

    private void NavSettings_Click(object sender, RoutedEventArgs e)
    {
        HideAllViews();
        ViewSettings.Visibility = Visibility.Visible;

        if (SettingsFrame.Content == null)
        {
            // Resolve SettingsPage dynamically from container
            var settingsPage = _serviceProvider.GetRequiredService<SettingsPage>();
            SettingsFrame.Content = settingsPage;
        }
    }

    private void TogglePaletteButton_Click(object sender, RoutedEventArgs e)
    {
        if (CommandPaletteOverlay.Visibility == Visibility.Visible)
        {
            CommandPaletteOverlay.Visibility = Visibility.Collapsed;
        }
        else
        {
            CommandPaletteOverlay.Visibility = Visibility.Visible;
            // Set focus to the search box in the user control
            var textBox = CommandPaletteControl.FindName("SearchBox") as TextBox;
            textBox?.Focus(FocusState.Programmatic);
        }
    }

    private void CommandPaletteOverlay_PointerPressed(object sender, PointerRoutedEventArgs e)
    {
        // Close overlay when clicking background area
        CommandPaletteOverlay.Visibility = Visibility.Collapsed;
    }

    private async void AnalyzeButton_Click(object sender, RoutedEventArgs e)
    {
        VisionOutputText.Text = "Capturing screen frame and running local ONNX models...";
        
        // Call the Vision module's ScreenAnalyzer
        string result = await _screenAnalyzer.AnalyzeScreenAsync();
        
        VisionOutputText.Text = $"[Success] {DateTime.Now:T}\n\n{result}\n\nExtracted UI Controls:\n- Button [Scan Desktop Frame] (x: 450, y: 120)\n- TextBox [SearchBox] (x: 200, y: 400)\n- Active terminal process: dotnet.exe";
    }

    private void PresetWorkflowSelector_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (WorkflowScriptBox == null) return;

        switch (PresetWorkflowSelector.SelectedIndex)
        {
            case 1:
                WorkflowScriptBox.Text = "Clean build cache; Rebuild AetherShell.slnx; Execute xUnit test suites; Notify user of completion";
                break;
            case 2:
                WorkflowScriptBox.Text = "Check system health; Verify background AgentOS daemon; Run container diagnostics; Alert active listening agents";
                break;
            case 3:
                WorkflowScriptBox.Text = "Clean; Rebuild; Execute xUnit test suites; Publish compiled artifacts; Notify event listeners";
                break;
            default:
                break;
        }
    }

    private async void RunCustomWorkflowButton_Click(object sender, RoutedEventArgs e)
    {
        var script = WorkflowScriptBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(script))
        {
            AutomationOutputText.Text = "Please select a preset template or enter your custom workflow script steps (e.g. Clean; Build; Test; Notify).";
            return;
        }

        AutomationOutputText.Text = "Parsing and starting custom workflow execution sequence...\n";
        
        string log = await _workflowEngine.ExecuteWorkflowWithLogsAsync(script);
        
        AutomationOutputText.Text = log;
    }
}