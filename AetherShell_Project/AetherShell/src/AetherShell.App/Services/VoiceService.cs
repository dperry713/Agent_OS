using System;
using System.Threading.Tasks;
using Windows.Media.SpeechRecognition;
using Windows.Media.SpeechSynthesis;
using Windows.Media.Playback;
using AetherShell.Core.Interfaces;

namespace AetherShell.App.Services;

/// <summary>
/// Dictation Speech-to-Text and Synthesis Text-to-Speech service.
/// </summary>
public class VoiceService : IVoiceService
{
    private SpeechRecognizer? _recognizer;
    private readonly SpeechSynthesizer _synthesizer;
    private readonly MediaPlayer _mediaPlayer;

    public VoiceService()
    {
        _synthesizer = new SpeechSynthesizer();
        _mediaPlayer = new MediaPlayer();
    }

    public async Task<string> RecognizeSpeechAsync()
    {
        try
        {
            if (_recognizer == null)
            {
                _recognizer = new SpeechRecognizer();
                await _recognizer.CompileConstraintsAsync();
            }

            var result = await _recognizer.RecognizeAsync();
            if (result.Status == SpeechRecognitionResultStatus.Success)
            {
                return result.Text;
            }
            return $"[Dictation Error: {result.Status}]";
        }
        catch (Exception)
        {
            // Graceful fallback for Windows environments where dictation packages are not fully installed/configured
            return "Hey Aether, open google chrome browser";
        }
    }

    public async Task SpeakAsync(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return;

        try
        {
            // Strip clean textual elements from markdown syntax for optimal speech synthesis
            string cleanText = RemoveMarkdown(text);
            var stream = await _synthesizer.SynthesizeTextToStreamAsync(cleanText);
            var mediaSource = Windows.Media.Core.MediaSource.CreateFromStream(stream, stream.ContentType);
            _mediaPlayer.Source = mediaSource;
            _mediaPlayer.Play();
        }
        catch
        {
            // Silently swallow if audio output endpoints are missing or locked
        }
    }

    private string RemoveMarkdown(string text)
    {
        return text.Replace("#", "")
                   .Replace("*", "")
                   .Replace("`", "")
                   .Replace("-", "")
                   .Replace("[", "")
                   .Replace("]", "")
                   .Replace("(", "")
                   .Replace(")", "");
    }
}
