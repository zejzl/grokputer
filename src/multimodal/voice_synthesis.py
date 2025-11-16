"""
Voice Synthesis Module
=====================

Text-to-speech functionality for interactive demos and accessibility.
Supports multiple TTS engines and voice customization.
"""

import asyncio
import logging
import queue
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class VoiceSynthesizer:
    """
    Text-to-speech synthesizer with multiple backend support.
    """

    def __init__(self, backend: str = "auto", voice_config: Optional[Dict[str, Any]] = None):
        """
        Initialize voice synthesizer.

        Args:
            backend: TTS backend ('pyttsx3', 'gtts', 'auto')
            voice_config: Voice configuration parameters
        """
        self.backend = backend
        self.voice_config = voice_config or {}
        self.engine = None
        self._init_engine()

        # Async queue for speech requests
        self.speech_queue = queue.Queue()
        self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.speech_thread.start()

        logger.info(f"Voice synthesizer initialized with {backend} backend")

    def _init_engine(self):
        """Initialize the TTS engine."""
        if self.backend == "pyttsx3" or self.backend == "auto":
            try:
                import pyttsx3

                self.engine = pyttsx3.init()
                self.backend = "pyttsx3"

                # Configure voice
                voices = self.engine.getProperty("voices")
                if voices:
                    # Select a female voice if available
                    for voice in voices:
                        if "female" in voice.name.lower() or "zira" in voice.name.lower():
                            self.engine.setProperty("voice", voice.id)
                            break

                # Set speech rate
                rate = self.voice_config.get("rate", 180)
                self.engine.setProperty("rate", rate)

                # Set volume
                volume = self.voice_config.get("volume", 0.8)
                self.engine.setProperty("volume", volume)

                logger.info("Pyttsx3 TTS engine initialized")
                return
            except ImportError:
                if self.backend == "pyttsx3":
                    raise ImportError("pyttsx3 not installed. Install with: pip install pyttsx3")
                logger.warning("pyttsx3 not available, trying gTTS")

        if self.backend == "gtts" or self.backend == "auto":
            try:
                import pygame
                from gtts import gTTS

                self.gtts = gTTS
                self.pygame = pygame
                self.backend = "gtts"
                logger.info("gTTS TTS engine initialized")
                return
            except ImportError:
                if self.backend == "gtts":
                    raise ImportError("gTTS or pygame not installed. Install with: pip install gTTS pygame")
                logger.warning("gTTS not available")

        if self.backend == "auto":
            logger.warning("No TTS backend available. Voice synthesis disabled.")
            self.backend = None

    def speak(self, text: str, async_mode: bool = True) -> bool:
        """
        Convert text to speech.

        Args:
            text: Text to speak
            async_mode: If True, queue for async processing

        Returns:
            True if speech was queued/started successfully
        """
        if not self.backend:
            logger.warning("No TTS backend available")
            return False

        if async_mode:
            self.speech_queue.put(text)
            return True
        else:
            return self._speak_sync(text)

    def _speak_sync(self, text: str) -> bool:
        """Synchronous speech synthesis."""
        try:
            if self.backend == "pyttsx3":
                self.engine.say(text)
                self.engine.runAndWait()
                return True

            elif self.backend == "gtts":
                tts = self.gtts(text=text, lang="en", slow=False)
                tts.save("temp_speech.mp3")

                self.pygame.mixer.init()
                self.pygame.mixer.music.load("temp_speech.mp3")
                self.pygame.mixer.music.play()

                # Wait for playback to finish
                while self.pygame.mixer.music.get_busy():
                    time.sleep(0.1)

                # Cleanup
                import os

                try:
                    os.remove("temp_speech.mp3")
                except:
                    pass

                return True

        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            return False

    def _speech_worker(self):
        """Background worker for async speech processing."""
        while True:
            try:
                text = self.speech_queue.get(timeout=1)
                self._speak_sync(text)
                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Speech worker error: {e}")

    def stop(self):
        """Stop the synthesizer and cleanup."""
        if self.backend == "gtts":
            try:
                self.pygame.mixer.quit()
            except:
                pass

    def get_available_voices(self) -> list:
        """Get list of available voices."""
        if self.backend == "pyttsx3":
            voices = self.engine.getProperty("voices")
            return [voice.name for voice in voices] if voices else []
        return []

    def set_voice(self, voice_name: str):
        """Set the voice by name."""
        if self.backend == "pyttsx3":
            voices = self.engine.getProperty("voices")
            for voice in voices:
                if voice_name.lower() in voice.name.lower():
                    self.engine.setProperty("voice", voice.id)
                    logger.info(f"Voice set to: {voice.name}")
                    return
            logger.warning(f"Voice '{voice_name}' not found")


# Global synthesizer instance
_voice_synthesizer = None


def get_voice_synthesizer() -> VoiceSynthesizer:
    """Get the global voice synthesizer instance."""
    global _voice_synthesizer
    if _voice_synthesizer is None:
        _voice_synthesizer = VoiceSynthesizer()
    return _voice_synthesizer


def speak_text(text: str, async_mode: bool = True) -> bool:
    """
    Convenience function to speak text using the global synthesizer.

    Args:
        text: Text to speak
        async_mode: Asynchronous mode

    Returns:
        True if successful
    """
    synthesizer = get_voice_synthesizer()
    return synthesizer.speak(text, async_mode)


async def demo_voice_synthesis():
    """Demo function for voice synthesis."""
    print("Voice Synthesis Demo")
    print("===================")

    synthesizer = VoiceSynthesizer()

    # Test different texts
    test_texts = [
        "Hello! This is a voice synthesis demo.",
        "Grokputer is an advanced AI system.",
        "Voice synthesis makes interactions more natural.",
        "Thank you for listening to this demonstration.",
    ]

    for text in test_texts:
        print(f"Speaking: {text}")
        synthesizer.speak(text, async_mode=False)
        await asyncio.sleep(1)  # Brief pause between utterances

    print("Demo complete!")


if __name__ == "__main__":
    asyncio.run(demo_voice_synthesis())
