"""
UI Understanding Module for Grokputer.

Provides high-level understanding of user interfaces from screenshots and visual analysis.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .vision_processor import VisionProcessor

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """Represents a parsed UI element."""

    element_type: str
    label: str = ""
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    confidence: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List["UIElement"] = field(default_factory=list)


@dataclass
class UIUnderstanding:
    """Complete UI understanding result."""

    screenshot_path: str
    ui_hierarchy: List[UIElement] = field(default_factory=list)
    page_type: str = "unknown"
    primary_actions: List[str] = field(default_factory=list)
    navigation_elements: List[UIElement] = field(default_factory=list)
    content_areas: List[UIElement] = field(default_factory=list)
    accessibility_issues: List[str] = field(default_factory=list)


class UIUnderstandingModule:
    """
    Advanced UI understanding system that parses interface elements and provides
    semantic understanding of user interfaces.
    """

    def __init__(self):
        self.vision_processor = VisionProcessor()
        self.element_parsers = self._initialize_parsers()

    def _initialize_parsers(self) -> Dict[str, callable]:
        """Initialize element-specific parsers."""
        return {
            "button": self._parse_button,
            "text_input": self._parse_text_input,
            "navigation": self._parse_navigation,
            "content": self._parse_content_area,
            "form": self._parse_form,
        }

    async def understand_ui(self, screenshot_path: str) -> UIUnderstanding:
        """
        Perform comprehensive UI understanding from a screenshot.

        Args:
            screenshot_path: Path to the screenshot

        Returns:
            UIUnderstanding object with parsed interface information
        """
        understanding = UIUnderstanding(screenshot_path=screenshot_path)

        try:
            # Get basic screenshot analysis
            screenshot_analysis = await self.vision_processor.analyze_screenshot(screenshot_path)

            # Parse UI elements into semantic components
            ui_elements = self._parse_ui_elements(screenshot_analysis)
            understanding.ui_hierarchy = ui_elements

            # Determine page type
            understanding.page_type = self._classify_page_type(ui_elements)

            # Identify primary actions
            understanding.primary_actions = self._identify_primary_actions(ui_elements)

            # Extract navigation elements
            understanding.navigation_elements = self._extract_navigation_elements(ui_elements)

            # Identify content areas
            understanding.content_areas = self._extract_content_areas(ui_elements)

            # Check accessibility
            understanding.accessibility_issues = self._check_accessibility(ui_elements, screenshot_analysis)

        except Exception as e:
            logger.error(f"UI understanding failed: {e}")
            understanding.page_type = f"analysis_failed: {str(e)}"

        return understanding

    def _parse_ui_elements(self, screenshot_analysis: Dict[str, Any]) -> List[UIElement]:
        """Parse raw UI elements into semantic UI components."""
        elements = []

        try:
            ui_elements_data = screenshot_analysis.get("ui_elements", [])
            interactive_elements = screenshot_analysis.get("interactive_elements", [])
            text_regions = screenshot_analysis.get("text_regions", [])

            # Process detected UI elements
            for elem_data in ui_elements_data:
                element = self._create_ui_element(elem_data, text_regions)
                if element:
                    elements.append(element)

            # Process interactive elements
            for interactive in interactive_elements:
                element = self._create_interactive_element(interactive, text_regions)
                if element:
                    elements.append(element)

            # Build hierarchy
            elements = self._build_element_hierarchy(elements)

        except Exception as e:
            logger.error(f"UI element parsing failed: {e}")

        return elements

    def _create_ui_element(self, elem_data: Dict[str, Any], text_regions: List[Dict[str, Any]]) -> Optional[UIElement]:
        """Create a UIElement from raw element data."""
        try:
            elem_type = elem_data["type"]
            bbox = tuple(elem_data["bbox"])
            confidence = elem_data.get("confidence", 0.7)

            # Find associated text
            associated_text = self._find_associated_text(bbox, text_regions)

            element = UIElement(
                element_type=elem_type,
                label=associated_text or elem_type,
                bbox=bbox,
                confidence=confidence,
                properties=elem_data,
            )

            # Use specific parser if available
            if elem_type in self.element_parsers:
                self.element_parsers[elem_type](element, text_regions)

            return element

        except Exception as e:
            logger.error(f"UI element creation failed: {e}")
            return None

    def _create_interactive_element(
        self, interactive: Dict[str, Any], text_regions: List[Dict[str, Any]]
    ) -> Optional[UIElement]:
        """Create a UIElement for interactive components."""
        try:
            elem_type = interactive["type"]
            bbox = tuple(interactive["bbox"])
            confidence = interactive.get("confidence", 0.7)

            associated_text = self._find_associated_text(bbox, text_regions)

            element = UIElement(
                element_type=elem_type,
                label=associated_text or elem_type,
                bbox=bbox,
                confidence=confidence,
                properties={"interactive": True},
            )

            return element

        except Exception as e:
            logger.error(f"Interactive element creation failed: {e}")
            return None

    def _find_associated_text(self, bbox: Tuple[int, int, int, int], text_regions: List[Dict[str, Any]]) -> str:
        """Find text associated with a UI element based on proximity."""
        x, y, w, h = bbox
        element_center_x = x + w / 2
        element_center_y = y + h / 2

        closest_text = ""
        min_distance = float("inf")

        for region in text_regions:
            if region.get("bbox"):
                tx, ty, tw, th = region["bbox"]
                text_center_x = tx + tw / 2
                text_center_y = ty + th / 2

                distance = ((element_center_x - text_center_x) ** 2 + (element_center_y - text_center_y) ** 2) ** 0.5

                if distance < min_distance and distance < 50:  # Within 50 pixels
                    min_distance = distance
                    closest_text = region["text"]

        return closest_text

    def _build_element_hierarchy(self, elements: List[UIElement]) -> List[UIElement]:
        """Build a hierarchical structure from flat UI elements."""
        # Simple hierarchy building based on containment
        root_elements = []

        for element in elements:
            contained_by = None
            for other in elements:
                if other != element and self._is_contained(element.bbox, other.bbox):
                    if contained_by is None or self._bbox_area(other.bbox) < self._bbox_area(contained_by.bbox):
                        contained_by = other

            if contained_by:
                contained_by.children.append(element)
            else:
                root_elements.append(element)

        return root_elements

    def _is_contained(self, inner_bbox: Tuple[int, int, int, int], outer_bbox: Tuple[int, int, int, int]) -> bool:
        """Check if one bbox is contained within another."""
        ix, iy, iw, ih = inner_bbox
        ox, oy, ow, oh = outer_bbox

        return ix >= ox and iy >= oy and ix + iw <= ox + ow and iy + ih <= oy + oh

    def _bbox_area(self, bbox: Tuple[int, int, int, int]) -> int:
        """Calculate bounding box area."""
        _, _, w, h = bbox
        return w * h

    def _parse_button(self, element: UIElement, text_regions: List[Dict[str, Any]]):
        """Parse button-specific properties."""
        element.properties["action_type"] = "click"
        element.properties["style"] = "primary"  # Could be enhanced with color analysis

    def _parse_text_input(self, element: UIElement, text_regions: List[Dict[str, Any]]):
        """Parse text input-specific properties."""
        element.properties["input_type"] = "text"
        element.properties["placeholder"] = element.label if element.label != "text_input" else ""

    def _parse_navigation(self, element: UIElement, text_regions: List[Dict[str, Any]]):
        """Parse navigation element properties."""
        element.properties["nav_type"] = "menu"

    def _parse_content_area(self, element: UIElement, text_regions: List[Dict[str, Any]]):
        """Parse content area properties."""
        element.properties["content_type"] = "text"

    def _parse_form(self, element: UIElement, text_regions: List[Dict[str, Any]]):
        """Parse form properties."""
        element.properties["form_action"] = "submit"

    def _classify_page_type(self, ui_elements: List[UIElement]) -> str:
        """Classify the type of page based on UI elements."""
        element_types = [elem.element_type for elem in ui_elements]

        # Simple classification logic
        if "text_input" in element_types and "button" in element_types:
            return "form_page"
        elif "navigation" in element_types or len([e for e in element_types if "button" in e]) > 3:
            return "application_interface"
        elif len([e for e in element_types if "content" in e]) > 0:
            return "content_page"
        else:
            return "unknown_interface"

    def _identify_primary_actions(self, ui_elements: List[UIElement]) -> List[str]:
        """Identify primary user actions available on the page."""
        actions = []

        for element in ui_elements:
            if "button" in element.element_type:
                if "submit" in element.label.lower() or "save" in element.label.lower():
                    actions.append("submit_form")
                elif "cancel" in element.label.lower():
                    actions.append("cancel_action")
                elif "search" in element.label.lower():
                    actions.append("search")
                else:
                    actions.append(f"click_{element.label}")

            elif element.element_type == "text_input":
                actions.append("input_text")

        return list(set(actions))  # Remove duplicates

    def _extract_navigation_elements(self, ui_elements: List[UIElement]) -> List[UIElement]:
        """Extract navigation-related elements."""
        navigation = []

        for element in ui_elements:
            if (
                "nav" in element.element_type.lower()
                or "menu" in element.label.lower()
                or element.element_type == "sidebar"
            ):
                navigation.append(element)

        return navigation

    def _extract_content_areas(self, ui_elements: List[UIElement]) -> List[UIElement]:
        """Extract main content areas."""
        content = []

        for element in ui_elements:
            if (
                "content" in element.element_type
                or "panel" in element.element_type
                or element.element_type == "text_input"
            ):
                content.append(element)

        return content

    def _check_accessibility(self, ui_elements: List[UIElement], screenshot_analysis: Dict[str, Any]) -> List[str]:
        """Check for accessibility issues."""
        issues = []

        # Check for missing labels
        for element in ui_elements:
            if element.element_type in ["button", "text_input"] and not element.label:
                issues.append(f"Missing label for {element.element_type} at {element.bbox}")

        # Check color contrast
        color_scheme = screenshot_analysis.get("color_scheme", {})
        if color_scheme.get("contrast_ratio", 1.0) < 0.5:
            issues.append("Low color contrast may affect readability")

        # Check for interactive elements without clear purpose
        interactive_count = len([e for e in ui_elements if "interactive" in e.properties])
        if interactive_count == 0:
            issues.append("No interactive elements detected")

        return issues

    def to_dict(self, understanding: UIUnderstanding) -> Dict[str, Any]:
        """Convert UIUnderstanding to dictionary for serialization."""

        def element_to_dict(element: UIElement) -> Dict[str, Any]:
            return {
                "element_type": element.element_type,
                "label": element.label,
                "bbox": element.bbox,
                "confidence": element.confidence,
                "properties": element.properties,
                "children": [element_to_dict(child) for child in element.children],
            }

        return {
            "screenshot_path": understanding.screenshot_path,
            "ui_hierarchy": [element_to_dict(elem) for elem in understanding.ui_hierarchy],
            "page_type": understanding.page_type,
            "primary_actions": understanding.primary_actions,
            "navigation_elements": [element_to_dict(elem) for elem in understanding.navigation_elements],
            "content_areas": [element_to_dict(elem) for elem in understanding.content_areas],
            "accessibility_issues": understanding.accessibility_issues,
        }
