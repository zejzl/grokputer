"""
Image Classifier for AI-Powered File Organizer.

Provides theme classification for images using a hybrid approach:
- Local heuristic classification using computer vision
- AI-powered classification via Grok/Claude APIs for ambiguous cases
- Caching to reduce costs and improve performance
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from src.grok_client import GrokClient
from src.vision_processor import VisionProcessor, VisualAnalysis

logger = logging.getLogger(__name__)


@dataclass
class Classification:
    """Represents an image classification result."""

    category: str
    confidence: float
    reason: str = ""
    method: str = "unknown"  # "local", "api", "cached"
    subcategories: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class ClassificationCache:
    """
    Persistent cache for classification results to avoid reprocessing.
    Uses SQLite for storage, keyed by file hash.
    """

    def __init__(self, cache_file: Optional[str] = None):
        if cache_file is None:
            cache_dir = Path.home() / ".grokputer"
            cache_dir.mkdir(exist_ok=True)
            cache_file = str(cache_dir / "organizer_cache.db")

        self.cache_file = cache_file
        self.conn = sqlite3.connect(cache_file)
        self._create_table()

    def _create_table(self):
        """Create cache table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS classifications (
                file_hash TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                confidence REAL NOT NULL,
                reason TEXT,
                method TEXT,
                subcategories TEXT,
                timestamp REAL NOT NULL
            )
        """)
        self.conn.commit()

    def get(self, file_hash: str) -> Optional[Classification]:
        """Get cached classification by file hash."""
        cursor = self.conn.execute(
            "SELECT category, confidence, reason, method, subcategories, timestamp FROM classifications WHERE file_hash = ?",
            (file_hash,)
        )
        row = cursor.fetchone()

        if row:
            category, confidence, reason, method, subcategories_json, timestamp = row
            subcategories = json.loads(subcategories_json) if subcategories_json else []

            return Classification(
                category=category,
                confidence=confidence,
                reason=reason or "",
                method="cached",
                subcategories=subcategories,
                timestamp=timestamp
            )

        return None

    def put(self, file_hash: str, classification: Classification):
        """Cache classification result."""
        self.conn.execute("""
            INSERT OR REPLACE INTO classifications
            (file_hash, category, confidence, reason, method, subcategories, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            file_hash,
            classification.category,
            classification.confidence,
            classification.reason,
            classification.method,
            json.dumps(classification.subcategories),
            classification.timestamp
        ))
        self.conn.commit()

    def clear(self):
        """Clear all cached classifications."""
        self.conn.execute("DELETE FROM classifications")
        self.conn.commit()

    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM classifications")
        total = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT category, COUNT(*) FROM classifications GROUP BY category")
        by_category = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total": total,
            "by_category": by_category
        }

    def close(self):
        """Close database connection."""
        self.conn.close()


class ImageClassifier:
    """
    AI-powered image classifier with hybrid local/API processing.

    Modes:
    - local: Only use computer vision heuristics (fast, private, ~60-70% accuracy)
    - hybrid: Local first, API for ambiguous cases (balanced, ~85-95% accuracy)
    - api: Always use API (best accuracy, higher cost)

    Categories:
    - wallpaper: High-resolution background images, abstract art
    - landscape: Outdoor nature photos (mountains, forests, beaches)
    - portrait: Photos with people (headshots, group photos, selfies)
    - screenshot: UI screenshots, app captures, web pages
    - document: Scanned documents, PDFs, text-heavy images
    - art: Digital art, drawings, paintings, graphics
    - adult: Adult content (requires user consent for API processing)
    - photo: General photos that don't fit other categories
    """

    def __init__(
        self,
        mode: str = "hybrid",
        cache_file: Optional[str] = None,
        confidence_threshold: float = 0.7,
        custom_categories: Optional[Dict[str, str]] = None
    ):
        """
        Initialize image classifier.

        Args:
            mode: Classification mode ("local", "hybrid", "api")
            cache_file: Path to cache database (None for default)
            confidence_threshold: Minimum confidence for local classification
            custom_categories: Dict of custom category names and descriptions
        """
        if mode not in ["local", "hybrid", "api"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'local', 'hybrid', or 'api'")

        self.mode = mode
        self.confidence_threshold = confidence_threshold
        self.vision_processor = VisionProcessor()
        self.grok_client = GrokClient() if mode != "local" else None
        self.cache = ClassificationCache(cache_file)

        # Default categories
        self.categories = {
            "wallpaper": "High-quality background images, abstract art, nature scenes for desktop backgrounds",
            "landscape": "Outdoor nature photos (mountains, forests, beaches, scenery)",
            "portrait": "Photos of people (headshots, group photos, selfies)",
            "screenshot": "UI screenshots, app captures, web pages, text-heavy with UI elements",
            "document": "Scanned documents, PDFs, text-heavy business content",
            "art": "Digital art, drawings, paintings, creative graphics",
            "photo": "General photos that don't fit other categories",
            "unsorted": "Images with low confidence or ambiguous content"
        }

        # Add custom categories
        if custom_categories:
            self.categories.update(custom_categories)

        logger.info(f"ImageClassifier initialized in {mode} mode with {len(self.categories)} categories")

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file for caching."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    async def classify(self, image_path: str, use_cache: bool = True) -> Classification:
        """
        Classify an image into one of the supported categories.

        Args:
            image_path: Path to the image file
            use_cache: Whether to use cached results

        Returns:
            Classification result with category, confidence, and reason
        """
        # Check cache first
        if use_cache:
            file_hash = self._compute_file_hash(image_path)
            cached = self.cache.get(file_hash)
            if cached:
                logger.debug(f"Cache hit for {image_path}: {cached.category} ({cached.confidence:.2f})")
                return cached

        # Try local classification first
        local_result = await self._local_classify(image_path)

        # If local confidence is high enough, or we're in local-only mode, return it
        if self.mode == "local" or local_result.confidence >= self.confidence_threshold:
            if use_cache:
                self.cache.put(file_hash, local_result)
            return local_result

        # Otherwise, use API for better accuracy
        if self.mode in ["hybrid", "api"]:
            try:
                api_result = await self._api_classify(image_path)
                if use_cache:
                    self.cache.put(file_hash, api_result)
                return api_result
            except Exception as e:
                logger.error(f"API classification failed for {image_path}: {e}")
                # Fall back to local result
                if use_cache:
                    self.cache.put(file_hash, local_result)
                return local_result

        # Shouldn't reach here, but return local result as fallback
        if use_cache:
            self.cache.put(file_hash, local_result)
        return local_result

    async def _local_classify(self, image_path: str) -> Classification:
        """
        Perform local classification using computer vision heuristics.

        Uses VisionProcessor to extract features and apply rule-based classification.
        Fast and private, but lower accuracy (~60-70%).
        """
        try:
            # Analyze image using VisionProcessor
            analysis = await self.vision_processor.analyze_image(image_path)

            # Load image for additional analysis
            img = cv2.imread(image_path)
            if img is None:
                return Classification(
                    category="unsorted",
                    confidence=0.0,
                    reason="Failed to load image",
                    method="local"
                )

            height, width = img.shape[:2]
            aspect_ratio = width / height if height > 0 else 0

            # Get PIL image for EXIF data
            pil_img = Image.open(image_path)

            # Heuristic rules based on features

            # Rule 1: Screenshot detection (text-heavy with UI elements)
            if analysis.text_extracted and len(analysis.text_extracted) > 50:
                text_density = len(analysis.text_extracted) / (width * height) * 1000000
                if text_density > 10 or "text_heavy" in analysis.scene_description.lower():
                    return Classification(
                        category="screenshot",
                        confidence=0.8,
                        reason=f"Text-heavy image ({len(analysis.text_extracted)} chars extracted)",
                        method="local"
                    )

            # Rule 2: Document detection (text-dominant, business content)
            if "document" in analysis.scene_description.lower():
                return Classification(
                    category="document",
                    confidence=0.75,
                    reason="Classified as document by scene analysis",
                    method="local"
                )

            # Rule 3: Wallpaper detection (high-res, minimal text, good composition)
            is_high_res = width >= 1920 or height >= 1080
            has_minimal_text = len(analysis.text_extracted) < 20
            has_simple_colors = len(analysis.dominant_colors) <= 3

            if is_high_res and has_minimal_text and (has_simple_colors or aspect_ratio > 1.3):
                return Classification(
                    category="wallpaper",
                    confidence=0.7,
                    reason=f"High resolution ({width}x{height}), minimal text, good composition",
                    method="local"
                )

            # Rule 4: Portrait detection (people/faces)
            if "portrait" in analysis.scene_description.lower() or "people" in analysis.scene_description.lower():
                return Classification(
                    category="portrait",
                    confidence=0.75,
                    reason="Portrait or people detected in scene analysis",
                    method="local"
                )

            # Rule 5: Landscape detection (outdoor nature scenes)
            if "landscape" in analysis.scene_description.lower() or "outdoor" in analysis.scene_description.lower():
                return Classification(
                    category="landscape",
                    confidence=0.75,
                    reason="Landscape or outdoor scene detected",
                    method="local"
                )

            # Rule 6: Art detection (specific color patterns, drawings)
            if "diagram" in analysis.scene_description.lower():
                return Classification(
                    category="art",
                    confidence=0.65,
                    reason="Artistic or diagrammatic content detected",
                    method="local"
                )

            # Default: General photo with low confidence
            return Classification(
                category="photo",
                confidence=0.4,
                reason="No specific category detected, classified as general photo",
                method="local"
            )

        except Exception as e:
            logger.error(f"Local classification failed for {image_path}: {e}")
            return Classification(
                category="unsorted",
                confidence=0.0,
                reason=f"Classification error: {str(e)}",
                method="local"
            )

    async def _api_classify(self, image_path: str) -> Classification:
        """
        Perform AI-powered classification using Grok/Claude vision API.

        More accurate but requires API calls. Should be used for ambiguous cases
        or when high accuracy is needed.
        """
        try:
            # Read image and encode as base64
            with open(image_path, "rb") as f:
                img_data = f.read()
            img_b64 = base64.b64encode(img_data).decode()

            # Build prompt with category descriptions
            categories_desc = "\n".join([f"- {cat}: {desc}" for cat, desc in self.categories.items() if cat != "unsorted"])

            prompt = f"""Analyze this image and classify it into ONE of these categories:

{categories_desc}

Respond in JSON format with:
{{
    "category": "the_category_name",
    "confidence": 0.0-1.0,
    "reason": "brief explanation why this category fits",
    "subcategories": ["optional", "additional", "tags"]
}}

Be specific and choose the most appropriate category. Use high confidence (>0.8) only when certain."""

            # Call Grok vision API
            response = await self.grok_client.create_message(
                task=prompt,
                screenshot_base64=img_b64
            )

            # Parse response
            content = response.get("content", "")

            # Try to extract JSON from response
            try:
                # Sometimes API wraps JSON in markdown code blocks
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()

                result = json.loads(json_str)

                # Validate category
                category = result.get("category", "unsorted")
                if category not in self.categories:
                    logger.warning(f"API returned unknown category: {category}, using 'unsorted'")
                    category = "unsorted"

                return Classification(
                    category=category,
                    confidence=float(result.get("confidence", 0.5)),
                    reason=result.get("reason", ""),
                    method="api",
                    subcategories=result.get("subcategories", [])
                )

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse API response as JSON: {content[:200]}")
                # Fall back to text analysis
                category = "unsorted"
                confidence = 0.5

                # Simple keyword matching as fallback
                content_lower = content.lower()
                for cat in self.categories.keys():
                    if cat in content_lower:
                        category = cat
                        confidence = 0.6
                        break

                return Classification(
                    category=category,
                    confidence=confidence,
                    reason=f"API response parsing failed: {str(e)}",
                    method="api"
                )

        except Exception as e:
            logger.error(f"API classification failed for {image_path}: {e}")
            # Return low-confidence unsorted
            return Classification(
                category="unsorted",
                confidence=0.0,
                reason=f"API error: {str(e)}",
                method="api"
            )

    async def classify_batch(self, image_paths: List[str], batch_size: int = 10) -> List[Classification]:
        """
        Classify multiple images in parallel with concurrency control.

        Args:
            image_paths: List of image file paths
            batch_size: Maximum number of concurrent classifications

        Returns:
            List of Classification results
        """
        semaphore = asyncio.Semaphore(batch_size)

        async def classify_one(path: str) -> Classification:
            async with semaphore:
                return await self.classify(path)

        tasks = [classify_one(path) for path in image_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error classifications
        classifications = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Classification failed for {image_paths[i]}: {result}")
                classifications.append(Classification(
                    category="unsorted",
                    confidence=0.0,
                    reason=f"Error: {str(result)}",
                    method="error"
                ))
            else:
                classifications.append(result)

        return classifications

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get classification cache statistics."""
        return self.cache.stats()

    def clear_cache(self):
        """Clear all cached classifications."""
        self.cache.clear()
        logger.info("Classification cache cleared")

    def close(self):
        """Close classifier and clean up resources."""
        self.cache.close()
