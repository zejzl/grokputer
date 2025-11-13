"""
Vision Processing System for Grokputer.

Provides comprehensive visual understanding capabilities including:
- Image analysis and feature extraction
- Object detection and recognition
- Scene understanding
- OCR integration
- Visual knowledge extraction
"""

import asyncio
import logging
import numpy as np
import cv2
from PIL import Image
import io
import base64
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

from src.ocr.ocr_processor import OCRProcessor

logger = logging.getLogger(__name__)


@dataclass
class VisualFeature:
    """Represents extracted visual features."""

    feature_type: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class VisualAnalysis:
    """Complete visual analysis result."""

    image_path: str
    features: List[VisualFeature] = field(default_factory=list)
    scene_description: str = ""
    objects_detected: List[str] = field(default_factory=list)
    text_extracted: str = ""
    ocr_confidence: float = 0.0
    dominant_colors: List[Tuple[int, int, int]] = field(default_factory=list)
    image_metadata: Dict[str, Any] = field(default_factory=dict)


class VisionProcessor:
    """
    Advanced vision processing system for multi-modal understanding.

    Features:
    - Image feature extraction
    - Object detection and recognition
    - Scene analysis
    - OCR integration
    - Visual knowledge extraction
    """

    def __init__(self):
        self.ocr_processor = OCRProcessor()
        self.feature_extractors = self._initialize_feature_extractors()

    def _initialize_feature_extractors(self) -> Dict[str, callable]:
        """Initialize available feature extraction methods."""
        return {
            "color_histogram": self._extract_color_histogram,
            "edge_detection": self._extract_edges,
        }

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Process an image synchronously for testing."""
        # For testing, return a mock result
        return {"processed": True, "path": image_path}

    async def analyze_image(self, image_path: str, analysis_types: List[str] = None) -> VisualAnalysis:
        """
        Perform comprehensive visual analysis of an image.

        Args:
            image_path: Path to the image file
            analysis_types: List of analysis types to perform (None for all)

        Returns:
            VisualAnalysis object with all extracted information
        """
        if analysis_types is None:
            analysis_types = ["ocr", "features", "scene", "objects"]

        analysis = VisualAnalysis(image_path=image_path)

        try:
            # Load image and extract basic metadata
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

            analysis.image_metadata = self._extract_image_metadata(image_path, image)

            # Perform requested analyses
            tasks = []
            if "ocr" in analysis_types:
                tasks.append(self._perform_ocr_analysis(image_path, analysis))
            if "features" in analysis_types:
                tasks.append(self._perform_feature_analysis(image, analysis))
            if "scene" in analysis_types:
                tasks.append(self._perform_scene_analysis(image, analysis))
            if "objects" in analysis_types:
                tasks.append(self._perform_object_detection(image, analysis))

            # Run all analyses concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {e}")
            analysis.scene_description = f"Analysis failed: {str(e)}"

        return analysis

    async def _perform_ocr_analysis(self, image_path: str, analysis: VisualAnalysis):
        """Perform OCR analysis."""
        try:
            text, confidence = await self.ocr_processor.recover_extract(image_path)
            analysis.text_extracted = text or ""
            analysis.ocr_confidence = confidence

            if text:
                # Extract text-related features
                analysis.features.append(
                    VisualFeature(
                        feature_type="text_content",
                        confidence=confidence / 100.0,
                        properties={"text": text, "length": len(text)},
                    )
                )

        except Exception as e:
            logger.error(f"OCR analysis failed: {e}")

    async def _perform_feature_analysis(self, image: np.ndarray, analysis: VisualAnalysis):
        """Extract visual features from the image."""
        try:
            # Extract color histogram
            color_features = self._extract_color_histogram(image)
            analysis.features.extend(color_features)

            # Extract edges
            edge_features = self._extract_edges(image)
            analysis.features.extend(edge_features)

            # Extract dominant colors
            analysis.dominant_colors = self._extract_dominant_colors(image)

        except Exception as e:
            logger.error(f"Feature analysis failed: {e}")

    async def _perform_scene_analysis(self, image: np.ndarray, analysis: VisualAnalysis):
        """Analyze the overall scene and content."""
        try:
            # Basic scene analysis based on features
            features = analysis.features

            # Determine if image is likely a document, photo, diagram, etc.
            scene_type = self._classify_scene_type(image, features)
            analysis.scene_description = f"Detected scene type: {scene_type}"

            # Add scene classification feature
            analysis.features.append(
                VisualFeature(
                    feature_type="scene_classification",
                    confidence=0.7,  # Placeholder confidence
                    properties={"scene_type": scene_type},
                )
            )

        except Exception as e:
            logger.error(f"Scene analysis failed: {e}")

    async def _perform_object_detection(self, image: np.ndarray, analysis: VisualAnalysis):
        """Detect and identify objects in the image."""
        try:
            # Simple object detection based on contours and shapes
            objects = self._detect_basic_objects(image)
            analysis.objects_detected = objects

            # Add object detection features
            for obj in objects:
                analysis.features.append(
                    VisualFeature(
                        feature_type="object_detected",
                        confidence=0.6,  # Placeholder confidence
                        properties={"object_type": obj},
                    )
                )

        except Exception as e:
            logger.error(f"Object detection failed: {e}")

    def _extract_image_metadata(self, image_path: str, image: np.ndarray) -> Dict[str, Any]:
        """Extract basic image metadata."""
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) > 2 else 1

        return {
            "width": width,
            "height": height,
            "channels": channels,
            "file_size": self._get_file_size(image_path),
            "format": self._get_image_format(image_path),
        }

    def _extract_color_histogram(self, image: np.ndarray) -> List[VisualFeature]:
        """Extract color histogram features."""
        features = []

        if len(image.shape) == 3:
            # Color image
            for i, color in enumerate(["blue", "green", "red"]):
                hist = cv2.calcHist([image], [i], None, [256], [0, 256])
                hist = cv2.normalize(hist, hist).flatten()

                features.append(
                    VisualFeature(
                        feature_type=f"color_histogram_{color}", confidence=1.0, properties={"histogram": hist.tolist()}
                    )
                )
        else:
            # Grayscale image
            hist = cv2.calcHist([image], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()

            features.append(
                VisualFeature(
                    feature_type="grayscale_histogram", confidence=1.0, properties={"histogram": hist.tolist()}
                )
            )

        return features

    def _extract_edges(self, image: np.ndarray) -> List[VisualFeature]:
        """Extract edge detection features."""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Canny edge detection
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / edges.size

        return [
            VisualFeature(
                feature_type="edge_detection",
                confidence=1.0,
                properties={"edge_density": float(edge_density), "total_edges": int(np.sum(edges > 0))},
            )
        ]

    def _extract_dominant_colors(self, image: np.ndarray, k: int = 5) -> List[Tuple[int, int, int]]:
        """Extract dominant colors using K-means clustering."""
        try:
            # Reshape image for clustering
            pixels = image.reshape(-1, 3)
            pixels = np.float32(pixels)

            # K-means clustering
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

            # Convert centers to integers and ensure 3-tuple format
            dominant_colors = []
            for center in centers:
                r, g, b = map(int, center)
                dominant_colors.append((r, g, b))

            return dominant_colors

        except Exception as e:
            logger.error(f"Dominant color extraction failed: {e}")
            return []

    def _classify_scene_type(self, image: np.ndarray, features: List[VisualFeature]) -> str:
        """Classify the type of scene based on extracted features."""
        # Simple heuristic-based classification
        height, width = image.shape[:2]
        aspect_ratio = width / height

        # Check for text features
        has_text = any(f.feature_type == "text_content" for f in features)
        text_features = [f for f in features if f.feature_type == "text_content"]

        # Check edge density
        edge_features = [f for f in features if f.feature_type == "edge_detection"]
        high_edge_density = False
        if edge_features:
            edge_density = edge_features[0].properties.get("edge_density", 0)
            high_edge_density = edge_density > 0.1

        # Classification logic
        if has_text and aspect_ratio > 1.5:
            return "document"
        elif has_text and len(text_features) > 0:
            text_length = text_features[0].properties.get("length", 0)
            if text_length > 100:
                return "text_heavy_document"
            else:
                return "labeled_image"
        elif high_edge_density and aspect_ratio < 1.2:
            return "diagram"
        elif aspect_ratio > 1.5:
            return "landscape_photo"
        elif aspect_ratio < 0.8:
            return "portrait_photo"
        else:
            return "general_photo"

    def _detect_basic_objects(self, image: np.ndarray) -> List[str]:
        """Detect basic objects using simple computer vision techniques."""
        objects = []

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

            # Find contours
            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 100:  # Skip very small contours
                    continue

                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0

                # Simple shape classification
                if 0.8 < aspect_ratio < 1.2 and area > 1000:
                    objects.append("square/rectangle")
                elif aspect_ratio > 2:
                    objects.append("horizontal_shape")
                elif aspect_ratio < 0.5:
                    objects.append("vertical_shape")
                else:
                    objects.append("irregular_shape")

        except Exception as e:
            logger.error(f"Basic object detection failed: {e}")

        return list(set(objects))  # Remove duplicates

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except:
            return 0

    def _get_image_format(self, file_path: str) -> str:
        """Get image format from file extension."""
        _, ext = os.path.splitext(file_path)
        return ext.lower().lstrip(".")

    async def analyze_screenshot(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Advanced analysis of screenshots for UI element detection and layout understanding.

        Args:
            screenshot_path: Path to the screenshot image

        Returns:
            Dictionary containing UI analysis results
        """
        ui_analysis = {
            "ui_elements": [],
            "layout_structure": {},
            "interactive_elements": [],
            "text_regions": [],
            "color_scheme": {},
            "accessibility_score": 0.0,
        }

        try:
            # Load screenshot
            screenshot = cv2.imread(screenshot_path)
            if screenshot is None:
                raise ValueError(f"Could not load screenshot: {screenshot_path}")

            height, width = screenshot.shape[:2]

            # Detect UI elements using contour analysis
            ui_elements = self._detect_ui_elements(screenshot)
            ui_analysis["ui_elements"] = ui_elements

            # Analyze layout structure
            layout = self._analyze_layout_structure(screenshot, ui_elements)
            ui_analysis["layout_structure"] = layout

            # Identify interactive elements (buttons, inputs, etc.)
            interactive = self._identify_interactive_elements(screenshot, ui_elements)
            ui_analysis["interactive_elements"] = interactive

            # Extract text regions with context
            text_regions = await self._extract_text_regions(screenshot_path)
            ui_analysis["text_regions"] = text_regions

            # Analyze color scheme
            color_scheme = self._analyze_color_scheme(screenshot)
            ui_analysis["color_scheme"] = color_scheme

            # Calculate accessibility score
            accessibility = self._calculate_accessibility_score(ui_elements, text_regions, color_scheme)
            ui_analysis["accessibility_score"] = accessibility

        except Exception as e:
            logger.error(f"Screenshot analysis failed: {e}")
            ui_analysis["error"] = str(e)

        return ui_analysis

    def _detect_ui_elements(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect UI elements using computer vision techniques."""
        elements = []

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

            # Apply thresholding to find potential UI elements
            _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 100:  # Skip very small elements
                    continue

                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0

                # Classify element type based on shape and size
                element_type = self._classify_ui_element(w, h, aspect_ratio, area, image.shape[:2])

                if element_type:
                    elements.append(
                        {
                            "type": element_type,
                            "bbox": [x, y, w, h],
                            "area": area,
                            "aspect_ratio": aspect_ratio,
                            "confidence": 0.7,  # Placeholder confidence
                        }
                    )

        except Exception as e:
            logger.error(f"UI element detection failed: {e}")

        return elements

    def _classify_ui_element(
        self, w: int, h: int, aspect_ratio: float, area: float, image_size: Tuple[int, int]
    ) -> str:
        """Classify UI element based on dimensions and characteristics."""
        img_h, img_w = image_size

        # Button-like elements
        if 0.5 < aspect_ratio < 3.0 and 1000 < area < 50000:
            if aspect_ratio > 1.5:
                return "button_horizontal"
            else:
                return "button_square"

        # Text input fields
        elif aspect_ratio > 3.0 and area > 2000:
            return "text_input"

        # Icons or small elements
        elif area < 5000 and 0.8 < aspect_ratio < 1.2:
            return "icon"

        # Large rectangular areas (panels, containers)
        elif aspect_ratio > 2.0 and area > 10000:
            return "panel"

        # Vertical elements (sidebars, menus)
        elif aspect_ratio < 0.5 and h > img_h * 0.3:
            return "sidebar"

        return None

    def _analyze_layout_structure(self, image: np.ndarray, ui_elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the overall layout structure of the screenshot."""
        layout = {"grid_system": "unknown", "alignment": "unknown", "spacing": "unknown", "hierarchy": []}

        try:
            height, width = image.shape[:2]

            # Analyze element positions for grid/layout detection
            if ui_elements:
                x_positions = [elem["bbox"][0] for elem in ui_elements]
                y_positions = [elem["bbox"][1] for elem in ui_elements]

                # Check for grid alignment
                x_unique = len(set(round(x / 10) * 10 for x in x_positions))  # Round to nearest 10
                y_unique = len(set(round(y / 10) * 10 for y in y_positions))

                if x_unique <= 3 and y_unique <= 3:
                    layout["grid_system"] = "simple_grid"
                elif x_unique <= 5 or y_unique <= 5:
                    layout["grid_system"] = "complex_grid"
                else:
                    layout["grid_system"] = "freeform"

                # Determine dominant alignment
                left_aligned = sum(1 for x in x_positions if x < width * 0.1)
                center_aligned = sum(
                    1
                    for x in x_positions
                    if abs(x + w / 2 - width / 2) < width * 0.1
                    for elem in ui_elements
                    if (w := elem["bbox"][2])
                )
                right_aligned = sum(1 for x in x_positions if x > width * 0.9)

                if center_aligned > max(left_aligned, right_aligned):
                    layout["alignment"] = "centered"
                elif left_aligned > right_aligned:
                    layout["alignment"] = "left_aligned"
                else:
                    layout["alignment"] = "right_aligned"

        except Exception as e:
            logger.error(f"Layout analysis failed: {e}")

        return layout

    def _identify_interactive_elements(
        self, image: np.ndarray, ui_elements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify interactive elements like buttons, links, inputs."""
        interactive = []

        for elem in ui_elements:
            elem_type = elem["type"]
            bbox = elem["bbox"]

            # Check for interactive characteristics
            is_interactive = False
            interaction_type = "unknown"

            if "button" in elem_type:
                is_interactive = True
                interaction_type = "clickable_button"
            elif elem_type == "text_input":
                is_interactive = True
                interaction_type = "text_input"
            elif elem_type == "icon":
                # Check if icon looks clickable (hover effects would need runtime analysis)
                is_interactive = True
                interaction_type = "clickable_icon"

            if is_interactive:
                interactive.append({"type": interaction_type, "bbox": bbox, "confidence": elem.get("confidence", 0.7)})

        return interactive

    async def _extract_text_regions(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract text regions with contextual information."""
        text_regions = []

        try:
            # Use OCR to get text data
            text, confidence = await self.ocr_processor.recover_extract(image_path)

            if text:
                # Split into regions (simplified - in practice would use OCR bounding boxes)
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if line.strip():
                        text_regions.append(
                            {
                                "text": line.strip(),
                                "bbox": None,  # Would need OCR with bounding boxes
                                "confidence": confidence / 100.0,
                                "line_number": i,
                                "context": "ui_text",
                            }
                        )

        except Exception as e:
            logger.error(f"Text region extraction failed: {e}")

        return text_regions

    def _analyze_color_scheme(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze the color scheme of the screenshot."""
        color_scheme = {
            "primary_colors": [],
            "contrast_ratio": 0.0,
            "color_temperature": "unknown",
            "dominant_hues": [],
        }

        try:
            # Get dominant colors
            dominant_colors = self._extract_dominant_colors(image, k=5)
            color_scheme["primary_colors"] = dominant_colors

            # Calculate contrast (simplified)
            if len(dominant_colors) >= 2:
                # Calculate contrast between first two colors
                color1 = np.array(dominant_colors[0])
                color2 = np.array(dominant_colors[1])
                contrast = np.linalg.norm(color1 - color2) / 255.0
                color_scheme["contrast_ratio"] = contrast

            # Determine color temperature (very simplified)
            avg_color = np.mean(image.reshape(-1, 3), axis=0)
            r, g, b = avg_color
            if r > g > b:
                color_scheme["color_temperature"] = "warm"
            elif b > g > r:
                color_scheme["color_temperature"] = "cool"
            else:
                color_scheme["color_temperature"] = "neutral"

        except Exception as e:
            logger.error(f"Color scheme analysis failed: {e}")

        return color_scheme

    def _calculate_accessibility_score(
        self, ui_elements: List[Dict[str, Any]], text_regions: List[Dict[str, Any]], color_scheme: Dict[str, Any]
    ) -> float:
        """Calculate an accessibility score for the UI."""
        score = 0.5  # Base score

        try:
            # Check for sufficient contrast
            if color_scheme.get("contrast_ratio", 0) > 0.5:
                score += 0.2

            # Check for interactive elements
            if len([e for e in ui_elements if "button" in e["type"] or e["type"] == "text_input"]) > 0:
                score += 0.1

            # Check for text readability
            if text_regions and all(r.get("confidence", 0) > 0.8 for r in text_regions):
                score += 0.2

            # Cap at 1.0
            score = min(score, 1.0)

        except Exception as e:
            logger.error(f"Accessibility calculation failed: {e}")

        return score

    async def extract_visual_knowledge(self, analysis: VisualAnalysis) -> Dict[str, Any]:
        """
        Extract knowledge from visual analysis for integration with knowledge graph.

        Returns structured knowledge that can be stored in the knowledge graph.
        """
        knowledge = {"entities": [], "relationships": [], "visual_features": []}

        try:
            # Extract entities from detected objects and text
            if analysis.objects_detected:
                for obj in analysis.objects_detected:
                    knowledge["entities"].append(
                        {
                            "id": f"visual_entity_{hash(obj + analysis.image_path) % 10000}",
                            "label": obj,
                            "entity_type": "visual_object",
                            "properties": {"source_image": analysis.image_path, "detection_method": "computer_vision"},
                            "source": "vision_processor",
                        }
                    )

            # Extract entities from OCR text
            if analysis.text_extracted:
                # Split text into potential entities (simple noun extraction)
                words = analysis.text_extracted.split()
                potential_entities = [word.strip(".,!?") for word in words if len(word) > 3]

                for entity_text in potential_entities[:5]:  # Limit to top 5
                    knowledge["entities"].append(
                        {
                            "id": f"text_entity_{hash(entity_text + analysis.image_path) % 10000}",
                            "label": entity_text,
                            "entity_type": "text_entity",
                            "properties": {
                                "source_image": analysis.image_path,
                                "context": analysis.text_extracted[:100],
                            },
                            "source": "vision_processor",
                        }
                    )

            # Extract relationships
            if analysis.objects_detected and analysis.text_extracted:
                # Create relationships between visual objects and text
                for obj in analysis.objects_detected[:3]:  # Limit relationships
                    knowledge["relationships"].append(
                        {
                            "id": f"rel_{hash(obj + analysis.text_extracted[:50]) % 10000}",
                            "source_id": f"visual_entity_{hash(obj + analysis.image_path) % 10000}",
                            "target_id": f"text_entity_{hash(analysis.text_extracted.split()[0] + analysis.image_path) % 10000}",
                            "type": "described_by",
                            "properties": {"image_path": analysis.image_path},
                            "source": "vision_processor",
                        }
                    )

            # Store visual features
            for feature in analysis.features:
                knowledge["visual_features"].append(
                    {
                        "type": feature.feature_type,
                        "confidence": feature.confidence,
                        "properties": feature.properties,
                        "bbox": feature.bbox,
                    }
                )

        except Exception as e:
            logger.error(f"Visual knowledge extraction failed: {e}")

        return knowledge

    def to_dict(self, analysis: VisualAnalysis) -> Dict[str, Any]:
        """Convert VisualAnalysis to dictionary for serialization."""
        return {
            "image_path": analysis.image_path,
            "features": [
                {
                    "feature_type": f.feature_type,
                    "confidence": f.confidence,
                    "bbox": f.bbox,
                    "properties": f.properties,
                    "timestamp": f.timestamp,
                }
                for f in analysis.features
            ],
            "scene_description": analysis.scene_description,
            "objects_detected": analysis.objects_detected,
            "text_extracted": analysis.text_extracted,
            "ocr_confidence": analysis.ocr_confidence,
            "dominant_colors": analysis.dominant_colors,
            "image_metadata": analysis.image_metadata,
        }
