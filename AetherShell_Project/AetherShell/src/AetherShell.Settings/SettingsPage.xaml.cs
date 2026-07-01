using Microsoft.UI.Xaml.Controls;

namespace AetherShell.Settings;

/// <summary>
/// A page that displays and manages settings.
/// </summary>
public sealed partial class SettingsPage : Page
{
    public SettingsPage()
    {
        this.InitializeComponent();
        SttToggle.IsOn = AetherSettings.IsSpeechToTextEnabled;
        TtsToggle.IsOn = AetherSettings.IsTextToSpeechEnabled;
    }

    private void SttToggle_Toggled(object sender, Microsoft.UI.Xaml.RoutedEventArgs e)
    {
        AetherSettings.IsSpeechToTextEnabled = SttToggle.IsOn;
    }

    private void TtsToggle_Toggled(object sender, Microsoft.UI.Xaml.RoutedEventArgs e)
    {
        AetherSettings.IsTextToSpeechEnabled = TtsToggle.IsOn;
    }
}
