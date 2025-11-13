"""
Audio Processing System for Grokputer.

Provides comprehensive audio understanding capabilities including:
- Speech-to-text conversion
- Audio feature extraction
- Sound classification
- Voice activity detection
- Audio knowledge extraction
"""

import asyncio
import logging
import numpy as np
import io
import wave
import audioop
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import struct
import math

logger = logging.getLogger(__name__)


@dataclass
class AudioFeature:
    """Represents extracted audio features."""

    feature_type: str
    confidence: float
    start_time: float
    end_time: float
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class AudioAnalysis:
    """Complete audio analysis result."""

    audio_path: str
    features: List[AudioFeature] = field(default_factory=list)
    transcription: str = ""
    transcription_confidence: float = 0.0
    detected_sounds: List[str] = field(default_factory=list)
    voice_activity_segments: List[Tuple[float, float]] = field(default_factory=list)
    audio_metadata: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    sample_rate: int = 0


class AudioProcessor:
    """
    Advanced audio processing system for multi-modal understanding.

    Features:
    - Speech-to-text conversion
    - Audio feature extraction
    - Sound classification
    - Voice activity detection
    - Audio knowledge extraction
    """

    def __init__(self):
        self.feature_extractors = self._initialize_feature_extractors()

    def _initialize_feature_extractors(self) -> Dict[str, callable]:
        """Initialize available feature extraction methods."""
        return {
            "mfcc": self._extract_mfcc,
            "spectral_centroid": self._extract_spectral_centroid,
            "rms_energy": self._extract_rms_energy,
            "zero_crossing_rate": self._extract_zero_crossing_rate,
        }

    async def analyze_audio(self, audio_path: str, analysis_types: List[str] = None) -> AudioAnalysis:
        """
        Perform comprehensive audio analysis.

        Args:
            audio_path: Path to the audio file
            analysis_types: List of analysis types to perform (None for all)

        Returns:
            AudioAnalysis object with all extracted information
        """
        if analysis_types is None:
            analysis_types = ["transcription", "features", "vad", "classification"]

        analysis = AudioAnalysis(audio_path=audio_path)

        try:
            # Load audio and extract basic metadata
            audio_data, sample_rate = self._load_audio(audio_path)
            if audio_data is None:
                raise ValueError(f"Could not load audio: {audio_path}")

            analysis.audio_metadata = self._extract_audio_metadata(audio_path, audio_data, sample_rate)
            analysis.duration = len(audio_data) / sample_rate
            analysis.sample_rate = sample_rate

            # Perform requested analyses
            tasks = []
            if "transcription" in analysis_types:
                tasks.append(self._perform_transcription_analysis(audio_data, sample_rate, analysis))
            if "features" in analysis_types:
                tasks.append(self._perform_feature_analysis(audio_data, sample_rate, analysis))
            if "vad" in analysis_types:
                tasks.append(self._perform_vad_analysis(audio_data, sample_rate, analysis))
            if "classification" in analysis_types:
                tasks.append(self._perform_sound_classification(audio_data, sample_rate, analysis))

            # Run all analyses concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error analyzing audio {audio_path}: {e}")
            analysis.transcription = f"Analysis failed: {str(e)}"

        return analysis

    def _load_audio(self, audio_path: str) -> Tuple[Optional[np.ndarray], int]:
        """Load audio file and return data and sample rate."""
        try:
            with wave.open(audio_path, "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                num_frames = wav_file.getnframes()
                num_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()

                # Read raw audio data
                raw_data = wav_file.readframes(num_frames)

                # Convert to numpy array
                if sample_width == 2:  # 16-bit
                    audio_data = np.frombuffer(raw_data, dtype=np.int16)
                elif sample_width == 4:  # 32-bit
                    audio_data = np.frombuffer(raw_data, dtype=np.int32)
                else:
                    audio_data = np.frombuffer(raw_data, dtype=np.int8)

                # Convert to mono if stereo
                if num_channels == 2:
                    audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(audio_data.dtype)

                # Normalize to float32 between -1 and 1
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                elif audio_data.dtype == np.int32:
                    audio_data = audio_data.astype(np.float32) / 2147483648.0
                elif audio_data.dtype == np.int8:
                    audio_data = audio_data.astype(np.float32) / 128.0

                return audio_data, sample_rate

        except Exception as e:
            logger.error(f"Failed to load audio {audio_path}: {e}")
            return None, 0

    async def _perform_transcription_analysis(self, audio_data: np.ndarray, sample_rate: int, analysis: AudioAnalysis):
        """Perform speech-to-text analysis."""
        try:
            # Placeholder for speech-to-text integration
            # In a real implementation, this would use a service like Google Speech-to-Text,
            # Azure Speech Services, or a local model like Whisper

            # For now, we'll simulate transcription with basic analysis
            transcription = self._simulate_transcription(audio_data, sample_rate)
            analysis.transcription = transcription
            analysis.transcription_confidence = 0.7  # Placeholder confidence

            if transcription:
                # Extract transcription-related features
                analysis.features.append(
                    AudioFeature(
                        feature_type="speech_content",
                        confidence=analysis.transcription_confidence,
                        start_time=0.0,
                        end_time=analysis.duration,
                        properties={"text": transcription, "length": len(transcription)},
                    )
                )

        except Exception as e:
            logger.error(f"Transcription analysis failed: {e}")

    async def _perform_feature_analysis(self, audio_data: np.ndarray, sample_rate: int, analysis: AudioAnalysis):
        """Extract audio features."""
        try:
            # Extract various audio features
            frame_length = int(0.025 * sample_rate)  # 25ms frames
            hop_length = int(0.010 * sample_rate)  # 10ms hop

            # Extract MFCC features
            mfcc_features = self._extract_mfcc(audio_data, sample_rate, frame_length, hop_length)
            analysis.features.extend(mfcc_features)

            # Extract spectral centroid
            centroid_features = self._extract_spectral_centroid(audio_data, sample_rate, frame_length, hop_length)
            analysis.features.extend(centroid_features)

            # Extract RMS energy
            energy_features = self._extract_rms_energy(audio_data, sample_rate, frame_length, hop_length)
            analysis.features.extend(energy_features)

        except Exception as e:
            logger.error(f"Feature analysis failed: {e}")

    async def _perform_vad_analysis(self, audio_data: np.ndarray, sample_rate: int, analysis: AudioAnalysis):
        """Perform voice activity detection."""
        try:
            # Simple energy-based VAD
            frame_length = int(0.025 * sample_rate)
            hop_length = int(0.010 * sample_rate)

            vad_segments = self._detect_voice_activity(audio_data, sample_rate, frame_length, hop_length)
            analysis.voice_activity_segments = vad_segments

            # Add VAD features
            for start_time, end_time in vad_segments:
                analysis.features.append(
                    AudioFeature(
                        feature_type="voice_activity",
                        confidence=0.8,  # Placeholder confidence
                        start_time=start_time,
                        end_time=end_time,
                        properties={"duration": end_time - start_time},
                    )
                )

        except Exception as e:
            logger.error(f"VAD analysis failed: {e}")

    async def _perform_sound_classification(self, audio_data: np.ndarray, sample_rate: int, analysis: AudioAnalysis):
        """Perform sound classification."""
        try:
            # Simple sound classification based on features
            detected_sounds = self._classify_sounds(audio_data, sample_rate)
            analysis.detected_sounds = detected_sounds

            # Add sound classification features
            for sound_type in detected_sounds:
                analysis.features.append(
                    AudioFeature(
                        feature_type="sound_classification",
                        confidence=0.6,  # Placeholder confidence
                        start_time=0.0,
                        end_time=analysis.duration,
                        properties={"sound_type": sound_type},
                    )
                )

        except Exception as e:
            logger.error(f"Sound classification failed: {e}")

    def _extract_audio_metadata(self, audio_path: str, audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """Extract basic audio metadata."""
        duration = len(audio_data) / sample_rate

        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_data**2))

        # Calculate dynamic range
        if len(audio_data) > 0:
            dynamic_range = 20 * np.log10(
                np.max(np.abs(audio_data)) / np.max(np.abs(audio_data[np.abs(audio_data) > 1e-10]))
            )
        else:
            dynamic_range = 0.0

        return {
            "duration": duration,
            "sample_rate": sample_rate,
            "channels": 1,  # We convert to mono
            "rms_energy": float(rms),
            "dynamic_range_db": float(dynamic_range),
            "file_size": self._get_file_size(audio_path),
            "format": self._get_audio_format(audio_path),
        }

    def _extract_mfcc(
        self, audio_data: np.ndarray, sample_rate: int, frame_length: int, hop_length: int
    ) -> List[AudioFeature]:
        """Extract MFCC (Mel-frequency cepstral coefficients) features."""
        features = []

        try:
            # Simple MFCC-like features (simplified implementation)
            num_frames = (len(audio_data) - frame_length) // hop_length + 1

            for i in range(min(num_frames, 10)):  # Limit to first 10 frames for demo
                start_sample = i * hop_length
                end_sample = start_sample + frame_length
                frame = audio_data[start_sample:end_sample]

                # Simple spectral features as MFCC placeholder
                fft = np.fft.rfft(frame)
                magnitude = np.abs(fft)
                freqs = np.fft.rfftfreq(len(frame), 1 / sample_rate)

                # Extract some basic spectral features
                spectral_centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
                spectral_rolloff = freqs[np.where(np.cumsum(magnitude) >= 0.85 * np.sum(magnitude))[0][0]]

                features.append(
                    AudioFeature(
                        feature_type="mfcc_frame",
                        confidence=1.0,
                        start_time=start_sample / sample_rate,
                        end_time=end_sample / sample_rate,
                        properties={
                            "spectral_centroid": float(spectral_centroid),
                            "spectral_rolloff": float(spectral_rolloff),
                            "frame_index": i,
                        },
                    )
                )

        except Exception as e:
            logger.error(f"MFCC extraction failed: {e}")

        return features

    def _extract_spectral_centroid(
        self, audio_data: np.ndarray, sample_rate: int, frame_length: int, hop_length: int
    ) -> List[AudioFeature]:
        """Extract spectral centroid features."""
        features = []

        try:
            num_frames = (len(audio_data) - frame_length) // hop_length + 1

            for i in range(min(num_frames, 5)):  # Limit for demo
                start_sample = i * hop_length
                end_sample = start_sample + frame_length
                frame = audio_data[start_sample:end_sample]

                fft = np.fft.rfft(frame)
                magnitude = np.abs(fft)
                freqs = np.fft.rfftfreq(len(frame), 1 / sample_rate)

                centroid = np.sum(freqs * magnitude) / np.sum(magnitude)

                features.append(
                    AudioFeature(
                        feature_type="spectral_centroid",
                        confidence=1.0,
                        start_time=start_sample / sample_rate,
                        end_time=end_sample / sample_rate,
                        properties={"centroid_hz": float(centroid)},
                    )
                )

        except Exception as e:
            logger.error(f"Spectral centroid extraction failed: {e}")

        return features

    def _extract_rms_energy(
        self, audio_data: np.ndarray, sample_rate: int, frame_length: int, hop_length: int
    ) -> List[AudioFeature]:
        """Extract RMS energy features."""
        features = []

        try:
            num_frames = (len(audio_data) - frame_length) // hop_length + 1

            for i in range(min(num_frames, 5)):  # Limit for demo
                start_sample = i * hop_length
                end_sample = start_sample + frame_length
                frame = audio_data[start_sample:end_sample]

                rms = np.sqrt(np.mean(frame**2))

                features.append(
                    AudioFeature(
                        feature_type="rms_energy",
                        confidence=1.0,
                        start_time=start_sample / sample_rate,
                        end_time=end_sample / sample_rate,
                        properties={"energy": float(rms)},
                    )
                )

        except Exception as e:
            logger.error(f"RMS energy extraction failed: {e}")

        return features

    def _extract_zero_crossing_rate(
        self, audio_data: np.ndarray, sample_rate: int, frame_length: int, hop_length: int
    ) -> List[AudioFeature]:
        """Extract zero crossing rate features."""
        features = []

        try:
            num_frames = (len(audio_data) - frame_length) // hop_length + 1

            for i in range(min(num_frames, 5)):  # Limit for demo
                start_sample = i * hop_length
                end_sample = start_sample + frame_length
                frame = audio_data[start_sample:end_sample]

                # Count zero crossings
                zero_crossings = np.sum(np.abs(np.diff(np.sign(frame)))) / 2
                zcr = zero_crossings / len(frame)

                features.append(
                    AudioFeature(
                        feature_type="zero_crossing_rate",
                        confidence=1.0,
                        start_time=start_sample / sample_rate,
                        end_time=end_sample / sample_rate,
                        properties={"zcr": float(zcr)},
                    )
                )

        except Exception as e:
            logger.error(f"Zero crossing rate extraction failed: {e}")

        return features

    def _detect_voice_activity(
        self, audio_data: np.ndarray, sample_rate: int, frame_length: int, hop_length: int
    ) -> List[Tuple[float, float]]:
        """Detect voice activity using energy-based method."""
        segments = []

        try:
            num_frames = (len(audio_data) - frame_length) // hop_length + 1
            energy_threshold = np.mean(audio_data**2) * 1.5  # Adaptive threshold

            current_segment_start = None

            for i in range(num_frames):
                start_sample = i * hop_length
                end_sample = start_sample + frame_length
                frame = audio_data[start_sample:end_sample]

                energy = np.mean(frame**2)

                if energy > energy_threshold:
                    if current_segment_start is None:
                        current_segment_start = start_sample / sample_rate
                else:
                    if current_segment_start is not None:
                        end_time = end_sample / sample_rate
                        if end_time - current_segment_start > 0.1:  # Minimum segment length
                            segments.append((current_segment_start, end_time))
                        current_segment_start = None

            # Close any open segment
            if current_segment_start is not None:
                segments.append((current_segment_start, len(audio_data) / sample_rate))

        except Exception as e:
            logger.error(f"Voice activity detection failed: {e}")

        return segments

    def _classify_sounds(self, audio_data: np.ndarray, sample_rate: int) -> List[str]:
        """Classify sounds based on audio features."""
        sounds = []

        try:
            # Simple classification based on basic features
            rms = np.sqrt(np.mean(audio_data**2))
            zcr = np.mean(
                [
                    np.sum(np.abs(np.diff(np.sign(audio_data[i : i + int(0.025 * sample_rate)])))) / 2
                    for i in range(0, len(audio_data), int(0.010 * sample_rate))
                ]
            )

            # Basic heuristics
            if rms > 0.1:
                if zcr > 0.1:
                    sounds.append("high_frequency_noise")
                else:
                    sounds.append("low_frequency_sound")

                # Check for speech-like patterns
                if 0.05 < zcr < 0.15 and 0.01 < rms < 0.3:
                    sounds.append("possible_speech")

            if rms < 0.01:
                sounds.append("silence")

        except Exception as e:
            logger.error(f"Sound classification failed: {e}")

        return sounds if sounds else ["unknown"]

    def _simulate_transcription(self, audio_data: np.ndarray, sample_rate: int) -> str:
        """Simulate speech-to-text transcription (placeholder)."""
        # This is a placeholder - in real implementation, use actual STT service
        duration = len(audio_data) / sample_rate

        # Simple simulation based on audio characteristics
        rms = np.sqrt(np.mean(audio_data**2))

        if rms > 0.05 and duration > 1.0:
            return "This is simulated speech transcription. In a real implementation, this would contain the actual transcribed text from the audio."
        elif rms > 0.01:
            return "Short audio segment detected."
        else:
            return "Low audio activity detected."

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except:
            return 0

    def _get_audio_format(self, file_path: str) -> str:
        """Get audio format from file extension."""
        _, ext = os.path.splitext(file_path)
        return ext.lower().lstrip(".")

    async def extract_audio_knowledge(self, analysis: AudioAnalysis) -> Dict[str, Any]:
        """
        Extract knowledge from audio analysis for integration with knowledge graph.

        Returns structured knowledge that can be stored in the knowledge graph.
        """
        knowledge = {"entities": [], "relationships": [], "audio_features": []}

        try:
            # Extract entities from transcription
            if analysis.transcription:
                # Split transcription into potential entities
                words = analysis.transcription.split()
                potential_entities = [word.strip(".,!?") for word in words if len(word) > 3]

                for entity_text in potential_entities[:5]:  # Limit to top 5
                    knowledge["entities"].append(
                        {
                            "id": f"audio_entity_{hash(entity_text + analysis.audio_path) % 10000}",
                            "label": entity_text,
                            "entity_type": "audio_transcript_entity",
                            "properties": {
                                "source_audio": analysis.audio_path,
                                "context": analysis.transcription[:100],
                            },
                            "source": "audio_processor",
                        }
                    )

            # Extract entities from detected sounds
            for sound in analysis.detected_sounds:
                knowledge["entities"].append(
                    {
                        "id": f"sound_entity_{hash(sound + analysis.audio_path) % 10000}",
                        "label": sound,
                        "entity_type": "sound_type",
                        "properties": {"source_audio": analysis.audio_path, "confidence": 0.6},
                        "source": "audio_processor",
                    }
                )

            # Extract relationships
            if analysis.transcription and analysis.detected_sounds:
                # Create relationships between transcription and sounds
                for sound in analysis.detected_sounds[:2]:  # Limit relationships
                    knowledge["relationships"].append(
                        {
                            "id": f"rel_audio_{hash(sound + analysis.transcription[:50]) % 10000}",
                            "source_id": f"sound_entity_{hash(sound + analysis.audio_path) % 10000}",
                            "target_id": f"audio_entity_{hash(analysis.transcription.split()[0] + analysis.audio_path) % 10000}",
                            "type": "audio_context",
                            "properties": {"audio_path": analysis.audio_path},
                            "source": "audio_processor",
                        }
                    )

            # Store audio features
            for feature in analysis.features:
                knowledge["audio_features"].append(
                    {
                        "type": feature.feature_type,
                        "confidence": feature.confidence,
                        "start_time": feature.start_time,
                        "end_time": feature.end_time,
                        "properties": feature.properties,
                    }
                )

        except Exception as e:
            logger.error(f"Audio knowledge extraction failed: {e}")

        return knowledge

    def to_dict(self, analysis: AudioAnalysis) -> Dict[str, Any]:
        """Convert AudioAnalysis to dictionary for serialization."""
        return {
            "audio_path": analysis.audio_path,
            "features": [
                {
                    "feature_type": f.feature_type,
                    "confidence": f.confidence,
                    "start_time": f.start_time,
                    "end_time": f.end_time,
                    "properties": f.properties,
                    "timestamp": f.timestamp,
                }
                for f in analysis.features
            ],
            "transcription": analysis.transcription,
            "transcription_confidence": analysis.transcription_confidence,
            "detected_sounds": analysis.detected_sounds,
            "voice_activity_segments": analysis.voice_activity_segments,
            "audio_metadata": analysis.audio_metadata,
            "duration": analysis.duration,
            "sample_rate": analysis.sample_rate,
        }
