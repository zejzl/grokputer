"""
Multi-Modal Processor for Grokputer.

Unifies vision, audio, and text processing capabilities for comprehensive
multi-modal understanding and knowledge extraction.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .audio_processor import AudioAnalysis, AudioProcessor
from .vision_processor import VisionProcessor, VisualAnalysis

logger = logging.getLogger(__name__)


@dataclass
class MultiModalInput:
    """Represents a multi-modal input with various data types."""

    text: Optional[str] = None
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class MultiModalAnalysis:
    """Complete multi-modal analysis result."""

    input_data: MultiModalInput
    text_analysis: Optional[Dict[str, Any]] = None
    visual_analysis: Optional[VisualAnalysis] = None
    audio_analysis: Optional[AudioAnalysis] = None
    cross_modal_insights: List[Dict[str, Any]] = field(default_factory=list)
    integrated_summary: str = ""
    confidence_score: float = 0.0
    processing_time: float = 0.0


class MultiModalProcessor:
    """
    Unified multi-modal processor combining vision, audio, and text analysis.

    Features:
    - Coordinated processing of multiple modalities
    - Cross-modal correlation and insights
    - Integrated knowledge extraction
    - Confidence scoring and fusion
    """

    def __init__(self):
        self.vision_processor = VisionProcessor()
        self.audio_processor = AudioProcessor()
        self.text_processor = None  # Placeholder for future text processing enhancements

    async def process_multimodal_input(self, input_data: MultiModalInput) -> MultiModalAnalysis:
        """
        Process multi-modal input data.

        Args:
            input_data: MultiModalInput containing various data types

        Returns:
            MultiModalAnalysis with integrated results
        """
        start_time = datetime.now().timestamp()
        analysis = MultiModalAnalysis(input_data=input_data)

        try:
            # Process each modality concurrently
            tasks = []

            if input_data.text:
                tasks.append(self._process_text_modality(input_data.text, analysis))

            if input_data.image_path:
                tasks.append(self._process_visual_modality(input_data.image_path, analysis))

            if input_data.audio_path:
                tasks.append(self._process_audio_modality(input_data.audio_path, analysis))

            # Wait for all modality processing to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # Generate cross-modal insights
            await self._generate_cross_modal_insights(analysis)

            # Create integrated summary
            analysis.integrated_summary = self._create_integrated_summary(analysis)

            # Calculate overall confidence
            analysis.confidence_score = self._calculate_overall_confidence(analysis)

        except Exception as e:
            logger.error(f"Multi-modal processing failed: {e}")
            analysis.integrated_summary = f"Processing failed: {str(e)}"

        finally:
            analysis.processing_time = datetime.now().timestamp() - start_time

        return analysis

    async def _process_text_modality(self, text: str, analysis: MultiModalAnalysis):
        """Process text modality."""
        try:
            # Basic text analysis (can be enhanced with NLP models)
            text_analysis = {
                "content": text,
                "length": len(text),
                "word_count": len(text.split()),
                "language": self._detect_language(text),
                "sentiment": self._analyze_sentiment(text),
                "key_phrases": self._extract_key_phrases(text),
                "confidence": 0.8,
            }

            analysis.text_analysis = text_analysis

        except Exception as e:
            logger.error(f"Text processing failed: {e}")
            analysis.text_analysis = {"error": str(e)}

    async def _process_visual_modality(self, image_path: str, analysis: MultiModalAnalysis):
        """Process visual modality."""
        try:
            # Use vision processor for comprehensive analysis
            visual_analysis = await self.vision_processor.analyze_image(
                image_path, analysis_types=["ocr", "features", "scene", "objects"]
            )
            analysis.visual_analysis = visual_analysis

        except Exception as e:
            logger.error(f"Visual processing failed: {e}")

    async def _process_audio_modality(self, audio_path: str, analysis: MultiModalAnalysis):
        """Process audio modality."""
        try:
            # Use audio processor for comprehensive analysis
            audio_analysis = await self.audio_processor.analyze_audio(
                audio_path, analysis_types=["transcription", "features", "vad", "classification"]
            )
            analysis.audio_analysis = audio_analysis

        except Exception as e:
            logger.error(f"Audio processing failed: {e}")

    async def _generate_cross_modal_insights(self, analysis: MultiModalAnalysis):
        """Generate insights from cross-modal correlations."""
        insights = []

        try:
            # Text-Vision correlations
            if analysis.text_analysis and analysis.visual_analysis:
                text_vision_insights = self._correlate_text_vision(analysis.text_analysis, analysis.visual_analysis)
                insights.extend(text_vision_insights)

            # Text-Audio correlations
            if analysis.text_analysis and analysis.audio_analysis:
                text_audio_insights = self._correlate_text_audio(analysis.text_analysis, analysis.audio_analysis)
                insights.extend(text_audio_insights)

            # Vision-Audio correlations
            if analysis.visual_analysis and analysis.audio_analysis:
                vision_audio_insights = self._correlate_vision_audio(analysis.visual_analysis, analysis.audio_analysis)
                insights.extend(vision_audio_insights)

            # Three-way correlations
            if analysis.text_analysis and analysis.visual_analysis and analysis.audio_analysis:
                three_way_insights = self._correlate_three_modalities(
                    analysis.text_analysis, analysis.visual_analysis, analysis.audio_analysis
                )
                insights.extend(three_way_insights)

        except Exception as e:
            logger.error(f"Cross-modal insight generation failed: {e}")

        analysis.cross_modal_insights = insights

    def _correlate_text_vision(
        self, text_analysis: Dict[str, Any], visual_analysis: VisualAnalysis
    ) -> List[Dict[str, Any]]:
        """Generate insights from text-vision correlations."""
        insights = []

        try:
            text_content = text_analysis.get("content", "").lower()
            visual_text = visual_analysis.text_extracted.lower() if visual_analysis.text_extracted else ""

            # Check for text-visual consistency
            if text_content and visual_text:
                # Simple text matching (can be enhanced with semantic similarity)
                common_words = set(text_content.split()) & set(visual_text.split())
                if common_words:
                    insights.append(
                        {
                            "type": "text_visual_consistency",
                            "description": f"Text content matches visual text ({len(common_words)} common words)",
                            "confidence": 0.8,
                            "common_elements": list(common_words),
                        }
                    )

            # Check for scene description match
            scene_desc = visual_analysis.scene_description.lower()
            if scene_desc and any(word in text_content for word in scene_desc.split()):
                insights.append(
                    {
                        "type": "text_scene_correlation",
                        "description": "Text content relates to described visual scene",
                        "confidence": 0.7,
                    }
                )

            # Check for object mentions
            mentioned_objects = []
            for obj in visual_analysis.objects_detected:
                if obj.lower() in text_content:
                    mentioned_objects.append(obj)

            if mentioned_objects:
                insights.append(
                    {
                        "type": "object_text_correlation",
                        "description": f"Text mentions visually detected objects: {', '.join(mentioned_objects)}",
                        "confidence": 0.9,
                        "mentioned_objects": mentioned_objects,
                    }
                )

        except Exception as e:
            logger.error(f"Text-vision correlation failed: {e}")

        return insights

    def _correlate_text_audio(
        self, text_analysis: Dict[str, Any], audio_analysis: AudioAnalysis
    ) -> List[Dict[str, Any]]:
        """Generate insights from text-audio correlations."""
        insights = []

        try:
            text_content = text_analysis.get("content", "").lower()
            transcription = audio_analysis.transcription.lower() if audio_analysis.transcription else ""

            # Check transcription-text consistency
            if text_content and transcription:
                common_words = set(text_content.split()) & set(transcription.split())
                if common_words:
                    insights.append(
                        {
                            "type": "text_audio_consistency",
                            "description": f"Text content matches audio transcription ({len(common_words)} common words)",
                            "confidence": 0.8,
                            "common_elements": list(common_words),
                        }
                    )

            # Check for speech-related insights
            if audio_analysis.voice_activity_segments:
                speech_duration = sum(end - start for start, end in audio_analysis.voice_activity_segments)
                total_duration = audio_analysis.duration

                speech_ratio = speech_duration / total_duration if total_duration > 0 else 0

                insights.append(
                    {
                        "type": "speech_characteristics",
                        "description": f"Audio contains {speech_ratio:.1%} speech content",
                        "confidence": 0.9,
                        "speech_ratio": speech_ratio,
                        "speech_duration": speech_duration,
                    }
                )

            # Sentiment analysis correlation
            text_sentiment = text_analysis.get("sentiment")
            if text_sentiment and audio_analysis.detected_sounds:
                # Correlate sentiment with audio characteristics
                if "high_frequency_noise" in audio_analysis.detected_sounds and text_sentiment == "negative":
                    insights.append(
                        {
                            "type": "sentiment_audio_correlation",
                            "description": "Negative text sentiment correlates with agitated audio characteristics",
                            "confidence": 0.6,
                        }
                    )

        except Exception as e:
            logger.error(f"Text-audio correlation failed: {e}")

        return insights

    def _correlate_vision_audio(
        self, visual_analysis: VisualAnalysis, audio_analysis: AudioAnalysis
    ) -> List[Dict[str, Any]]:
        """Generate insights from vision-audio correlations."""
        insights = []

        try:
            # Check for audiovisual synchronization hints
            visual_duration = visual_analysis.image_metadata.get("duration", 0)
            audio_duration = audio_analysis.duration

            # For images, duration might be 0, so we focus on content correlation
            if visual_analysis.objects_detected and audio_analysis.transcription:
                # Check if audio mentions visual objects
                transcription = audio_analysis.transcription.lower()
                mentioned_objects = []

                for obj in visual_analysis.objects_detected:
                    if obj.lower() in transcription:
                        mentioned_objects.append(obj)

                if mentioned_objects:
                    insights.append(
                        {
                            "type": "visual_audio_correlation",
                            "description": f"Audio mentions visually detected objects: {', '.join(mentioned_objects)}",
                            "confidence": 0.8,
                            "mentioned_objects": mentioned_objects,
                        }
                    )

            # Scene-audio correlation
            scene_type = None
            for feature in visual_analysis.features:
                if feature.feature_type == "scene_classification":
                    scene_type = feature.properties.get("scene_type")
                    break

            if scene_type and audio_analysis.detected_sounds:
                # Correlate scene type with audio characteristics
                if scene_type == "document" and "silence" in audio_analysis.detected_sounds:
                    insights.append(
                        {
                            "type": "scene_audio_consistency",
                            "description": "Quiet audio consistent with document scene type",
                            "confidence": 0.7,
                        }
                    )

        except Exception as e:
            logger.error(f"Vision-audio correlation failed: {e}")

        return insights

    def _correlate_three_modalities(
        self, text_analysis: Dict[str, Any], visual_analysis: VisualAnalysis, audio_analysis: AudioAnalysis
    ) -> List[Dict[str, Any]]:
        """Generate insights from three-way modality correlations."""
        insights = []

        try:
            # Check for complete multimedia content consistency
            text_content = text_analysis.get("content", "").lower()
            visual_text = visual_analysis.text_extracted.lower() if visual_analysis.text_extracted else ""
            audio_transcription = audio_analysis.transcription.lower() if audio_analysis.transcription else ""

            # Three-way text consistency
            if text_content and visual_text and audio_transcription:
                text_sets = [set(text_content.split()), set(visual_text.split()), set(audio_transcription.split())]

                # Find common elements across all three
                common_all = text_sets[0] & text_sets[1] & text_sets[2]
                if common_all:
                    insights.append(
                        {
                            "type": "multimodal_consistency",
                            "description": f"All modalities contain consistent information ({len(common_all)} common elements)",
                            "confidence": 0.9,
                            "common_elements": list(common_all),
                        }
                    )

            # Cross-modal sentiment/emotion analysis
            text_sentiment = text_analysis.get("sentiment")
            visual_scene = None
            for feature in visual_analysis.features:
                if feature.feature_type == "scene_classification":
                    visual_scene = feature.properties.get("scene_type")
                    break

            audio_emotion = self._infer_audio_emotion(audio_analysis)

            if text_sentiment and audio_emotion:
                if text_sentiment == audio_emotion:
                    insights.append(
                        {
                            "type": "multimodal_emotion_consistency",
                            "description": f"Text and audio convey consistent {text_sentiment} emotion",
                            "confidence": 0.8,
                            "emotion": text_sentiment,
                        }
                    )

        except Exception as e:
            logger.error(f"Three-way correlation failed: {e}")

        return insights

    def _create_integrated_summary(self, analysis: MultiModalAnalysis) -> str:
        """Create an integrated summary of all modalities."""
        summary_parts = []

        try:
            if analysis.text_analysis:
                text_info = analysis.text_analysis
                summary_parts.append(f"Text: {text_info.get('word_count', 0)} words")

            if analysis.visual_analysis:
                visual_info = analysis.visual_analysis
                scene = visual_info.scene_description
                objects = len(visual_info.objects_detected)
                summary_parts.append(f"Visual: {scene}, {objects} objects detected")

            if analysis.audio_analysis:
                audio_info = analysis.audio_analysis
                duration = audio_info.duration
                sounds = len(audio_info.detected_sounds)
                has_speech = bool(audio_info.transcription)
                summary_parts.append(
                    f"Audio: {duration:.1f}s duration, {sounds} sound types{' with speech' if has_speech else ''}"
                )

            if analysis.cross_modal_insights:
                insights_count = len(analysis.cross_modal_insights)
                summary_parts.append(f"Cross-modal: {insights_count} insights generated")

            if summary_parts:
                return " | ".join(summary_parts)
            else:
                return "No content analyzed"

        except Exception as e:
            logger.error(f"Summary creation failed: {e}")
            return "Summary generation failed"

    def _calculate_overall_confidence(self, analysis: MultiModalAnalysis) -> float:
        """Calculate overall confidence score for the analysis."""
        confidences = []

        try:
            if analysis.text_analysis:
                confidences.append(analysis.text_analysis.get("confidence", 0.5))

            if analysis.visual_analysis:
                # Average of OCR confidence and feature confidences
                ocr_conf = analysis.visual_analysis.ocr_confidence
                feature_confs = [f.confidence for f in analysis.visual_analysis.features]
                avg_feature_conf = sum(feature_confs) / len(feature_confs) if feature_confs else 0.5
                visual_conf = (ocr_conf + avg_feature_conf) / 2
                confidences.append(visual_conf)

            if analysis.audio_analysis:
                # Average of transcription confidence and feature confidences
                trans_conf = analysis.audio_analysis.transcription_confidence
                feature_confs = [f.confidence for f in analysis.audio_analysis.features]
                avg_feature_conf = sum(feature_confs) / len(feature_confs) if feature_confs else 0.5
                audio_conf = (trans_conf + avg_feature_conf) / 2
                confidences.append(audio_conf)

            # Cross-modal insights boost confidence
            if analysis.cross_modal_insights:
                insight_confs = [insight.get("confidence", 0.5) for insight in analysis.cross_modal_insights]
                avg_insight_conf = sum(insight_confs) / len(insight_confs)
                confidences.append(avg_insight_conf * 0.8)  # Slightly lower weight

            if confidences:
                return sum(confidences) / len(confidences)
            else:
                return 0.0

        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.0

    def _detect_language(self, text: str) -> str:
        """Simple language detection (placeholder)."""
        # Placeholder implementation - in real system, use langdetect or similar
        return "en"

    def _analyze_sentiment(self, text: str) -> str:
        """Simple sentiment analysis (placeholder)."""
        # Placeholder implementation - in real system, use TextBlob or similar
        positive_words = ["good", "great", "excellent", "amazing", "wonderful"]
        negative_words = ["bad", "terrible", "awful", "horrible", "worst"]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text (placeholder)."""
        # Placeholder implementation - in real system, use NLP libraries
        words = text.split()
        # Simple extraction: words longer than 6 characters
        return [word.strip(".,!?") for word in words if len(word) > 6][:5]

    def _infer_audio_emotion(self, audio_analysis: AudioAnalysis) -> Optional[str]:
        """Infer emotion from audio characteristics (placeholder)."""
        # Placeholder implementation based on simple heuristics
        if not audio_analysis.detected_sounds:
            return None

        # Simple emotion inference based on sound types
        if "high_frequency_noise" in audio_analysis.detected_sounds:
            return "agitated"
        elif "silence" in audio_analysis.detected_sounds:
            return "calm"
        else:
            return "neutral"

    async def extract_multimodal_knowledge(self, analysis: MultiModalAnalysis) -> Dict[str, Any]:
        """
        Extract knowledge from multi-modal analysis for integration with knowledge graph.

        Returns structured knowledge that can be stored in the knowledge graph.
        """
        knowledge = {"entities": [], "relationships": [], "multimodal_features": []}

        try:
            # Extract knowledge from individual modalities
            if analysis.visual_analysis:
                visual_knowledge = await self.vision_processor.extract_visual_knowledge(analysis.visual_analysis)
                knowledge["entities"].extend(visual_knowledge.get("entities", []))
                knowledge["relationships"].extend(visual_knowledge.get("relationships", []))
                knowledge["multimodal_features"].extend(visual_knowledge.get("visual_features", []))

            if analysis.audio_analysis:
                audio_knowledge = await self.audio_processor.extract_audio_knowledge(analysis.audio_analysis)
                knowledge["entities"].extend(audio_knowledge.get("entities", []))
                knowledge["relationships"].extend(audio_knowledge.get("relationships", []))
                knowledge["multimodal_features"].extend(audio_knowledge.get("audio_features", []))

            # Extract cross-modal knowledge
            for insight in analysis.cross_modal_insights:
                insight_type = insight.get("type", "unknown")
                confidence = insight.get("confidence", 0.5)

                # Create insight entity
                insight_entity = {
                    "id": f"multimodal_insight_{hash(str(insight) + str(analysis.input_data.timestamp)) % 10000}",
                    "label": insight.get("description", "Cross-modal insight"),
                    "entity_type": "multimodal_insight",
                    "properties": {
                        "insight_type": insight_type,
                        "confidence": confidence,
                        "description": insight.get("description", ""),
                        "timestamp": analysis.input_data.timestamp,
                    },
                    "source": "multimodal_processor",
                }
                knowledge["entities"].append(insight_entity)

                # Create relationships based on insight type
                if insight_type == "text_visual_consistency":
                    common_elements = insight.get("common_elements", [])
                    for element in common_elements[:3]:  # Limit relationships
                        knowledge["relationships"].append(
                            {
                                "id": f"rel_multimodal_{hash(element + str(analysis.input_data.timestamp)) % 10000}",
                                "source_id": f"text_entity_{hash(element + str(analysis.input_data.image_path or '')) % 10000}",
                                "target_id": f"visual_entity_{hash(element + str(analysis.input_data.image_path or '')) % 10000}",
                                "type": "multimodal_consistent",
                                "properties": {"element": element},
                                "source": "multimodal_processor",
                            }
                        )

        except Exception as e:
            logger.error(f"Multi-modal knowledge extraction failed: {e}")

        return knowledge

    def to_dict(self, analysis: MultiModalAnalysis) -> Dict[str, Any]:
        """Convert MultiModalAnalysis to dictionary for serialization."""
        return {
            "input_data": {
                "text": analysis.input_data.text,
                "image_path": analysis.input_data.image_path,
                "audio_path": analysis.input_data.audio_path,
                "metadata": analysis.input_data.metadata,
                "timestamp": analysis.input_data.timestamp,
            },
            "text_analysis": analysis.text_analysis,
            "visual_analysis": (
                self.vision_processor.to_dict(analysis.visual_analysis) if analysis.visual_analysis else None
            ),
            "audio_analysis": (
                self.audio_processor.to_dict(analysis.audio_analysis) if analysis.audio_analysis else None
            ),
            "cross_modal_insights": analysis.cross_modal_insights,
            "integrated_summary": analysis.integrated_summary,
            "confidence_score": analysis.confidence_score,
            "processing_time": analysis.processing_time,
        }
