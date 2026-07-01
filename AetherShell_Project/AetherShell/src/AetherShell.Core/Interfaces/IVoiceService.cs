using System.Threading.Tasks;

namespace AetherShell.Core.Interfaces;

/// <summary>
/// Abstraction for speech-to-text and text-to-speech so AI agents don't depend on the App layer.
/// </summary>
public interface IVoiceService
{
    Task<string> RecognizeSpeechAsync();
    Task SpeakAsync(string text);
}
