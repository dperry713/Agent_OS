namespace AetherShell.Settings;

/// <summary>
/// Global settings registry to track voice and input state.
/// </summary>
public static class AetherSettings
{
    public static bool IsSpeechToTextEnabled { get; set; } = false;
    public static bool IsTextToSpeechEnabled { get; set; } = false;
}
