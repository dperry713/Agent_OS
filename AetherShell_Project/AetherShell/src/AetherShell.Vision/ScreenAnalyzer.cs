using System.Threading.Tasks;

namespace AetherShell.Vision;

/// <summary>
/// Screen understanding and OCR capabilities.
/// Uses Windows.Graphics.Capture + ONNX models.
/// </summary>
public class ScreenAnalyzer
{
    public async Task<string> AnalyzeScreenAsync()
    {
        // Capture screen, run OCR, describe UI elements for agent context
        return "Analyzed screen content: ...";
    }
}