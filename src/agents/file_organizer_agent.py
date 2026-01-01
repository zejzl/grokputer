"""
File Organizer Agent for Grokputer Pantheon System.

AI-powered image organization agent that classifies and organizes files
into categorized folders using vision AI and safe file operations.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessageBus, MessagePriority
from src.file_operations.organizer import (
    FileOrganizer,
    create_category_folders,
    scan_directory,
)
from src.observability.session_logger import SessionLogger
from src.vision.image_classifier import ImageClassifier

logger = logging.getLogger(__name__)


class FileOrganizerAgent(BaseAgent):
    """
    File Organizer Agent - AI-powered image categorization and organization.

    Capabilities:
    - Directory scanning with configurable file patterns
    - Vision-based theme classification (local + AI)
    - Batch processing with progress tracking
    - Safe file operations with rollback support
    - Dry-run mode for preview
    - Custom category support

    Message Types:
    - organize_directory: Organize images in a directory
    - scan_directory: Scan and preview organization plan
    - get_stats: Get classification statistics
    - clear_cache: Clear classification cache
    """

    def __init__(
        self,
        message_bus: MessageBus,
        session_logger: SessionLogger,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize File Organizer Agent.

        Args:
            message_bus: MessageBus for agent communication
            session_logger: Session logger for tracking
            config: Configuration dict with options:
                - mode: "local", "hybrid", "api" (default: "hybrid")
                - confidence_threshold: 0.0-1.0 (default: 0.7)
                - conflict_strategy: "skip", "rename", "dedupe", "overwrite" (default: "rename")
                - dry_run: True/False (default: True)
                - batch_size: Concurrent processing limit (default: 10)
                - custom_categories: Dict of additional categories
        """
        config = config or {}

        super().__init__(
            agent_id="file_organizer",
            message_bus=message_bus,
            session_logger=session_logger,
            config=config,
            heartbeat_interval=10.0
        )

        # Agent capabilities
        self.capabilities = [
            "organize_images",
            "classify_images",
            "scan_directory",
            "file_organization"
        ]

        # Configuration
        self.mode = config.get("mode", "hybrid")
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.conflict_strategy = config.get("conflict_strategy", "rename")
        self.dry_run = config.get("dry_run", True)
        self.batch_size = config.get("batch_size", 10)
        self.custom_categories = config.get("custom_categories", {})

        # Initialize components
        self.classifier = ImageClassifier(
            mode=self.mode,
            confidence_threshold=self.confidence_threshold,
            custom_categories=self.custom_categories
        )

        self.file_organizer = FileOrganizer(
            dry_run=self.dry_run,
            conflict_strategy=self.conflict_strategy
        )

        # Statistics
        self.stats = {
            "directories_organized": 0,
            "files_processed": 0,
            "files_moved": 0,
            "files_skipped": 0,
            "errors": 0
        }

        logger.info(
            f"FileOrganizerAgent initialized "
            f"(mode={self.mode}, dry_run={self.dry_run}, conflict={self.conflict_strategy})"
        )

    async def process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """
        Process incoming messages for file organization tasks.

        Supported message types:
        - organize_directory: Full organization workflow
        - scan_directory: Scan and preview only
        - get_stats: Get agent statistics
        - clear_cache: Clear classification cache
        """
        self._update_state("processing")

        try:
            message_type = message.message_type
            content = message.content

            if message_type == "organize_directory":
                return await self._organize_directory(content)

            elif message_type == "scan_directory":
                return await self._scan_directory(content)

            elif message_type == "get_stats":
                return await self._get_stats()

            elif message_type == "clear_cache":
                return await self._clear_cache()

            else:
                logger.warning(f"Unknown message type: {message_type}")
                return {
                    "status": "error",
                    "error": f"Unknown message type: {message_type}"
                }

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.on_error(e)
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            self._update_state("idle")

    async def _organize_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Organize images in a directory.

        Args:
            params: Dict with:
                - source: Source directory path
                - dest: Destination directory path (optional)
                - patterns: File patterns to match (optional)
                - dry_run: Override agent dry_run setting (optional)

        Returns:
            Dict with organization results
        """
        source = params.get("source")
        dest = params.get("dest", source)
        patterns = params.get("patterns", ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp", "*.bmp"])
        dry_run = params.get("dry_run", self.dry_run)

        if not source:
            return {"status": "error", "error": "Missing 'source' parameter"}

        logger.info(f"Organizing directory: {source} -> {dest} (dry_run={dry_run})")

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"organize_start: {source}"
        )

        # Update file organizer dry_run setting
        self.file_organizer.dry_run = dry_run

        # Step 1: Scan directory
        logger.info(f"Scanning directory: {source}")
        files = scan_directory(source, patterns=patterns, recursive=True)

        if not files:
            return {
                "status": "success",
                "message": "No files found matching patterns",
                "files_found": 0
            }

        logger.info(f"Found {len(files)} files to process")

        # Step 2: Classify images in batches
        logger.info("Classifying images...")
        classifications = await self.classifier.classify_batch(files, batch_size=self.batch_size)

        # Step 3: Create category folders
        categories = set(c.category for c in classifications)
        category_paths = create_category_folders(dest, list(categories))

        # Step 4: Build file mappings (source -> destination)
        file_mappings = {}
        for file_path, classification in zip(files, classifications):
            if classification.category in category_paths:
                dest_dir = category_paths[classification.category]
                file_name = Path(file_path).name
                dest_path = str(Path(dest_dir) / file_name)
                file_mappings[file_path] = dest_path

        # Step 5: Organize files
        logger.info(f"Organizing {len(file_mappings)} files...")

        # Progress callback for tracking
        def progress_callback(current, total, file_path):
            if current % 10 == 0 or current == total:
                logger.info(f"Progress: {current}/{total} files processed")

        result = self.file_organizer.organize_files(
            file_mappings,
            progress_callback=progress_callback
        )

        # Update agent statistics
        self.stats["directories_organized"] += 1
        self.stats["files_processed"] += result.processed
        self.stats["files_moved"] += result.moved
        self.stats["files_skipped"] += result.skipped
        self.stats["errors"] += result.errors

        # Build detailed result
        categories_summary = {}
        for classification in classifications:
            cat = classification.category
            if cat not in categories_summary:
                categories_summary[cat] = {
                    "count": 0,
                    "avg_confidence": 0.0
                }
            categories_summary[cat]["count"] += 1
            categories_summary[cat]["avg_confidence"] += classification.confidence

        # Calculate averages
        for cat, data in categories_summary.items():
            if data["count"] > 0:
                data["avg_confidence"] = data["avg_confidence"] / data["count"]

        response = {
            "status": "success",
            "dry_run": dry_run,
            "source": source,
            "dest": dest,
            "files_found": len(files),
            "files_processed": result.processed,
            "files_moved": result.moved,
            "files_skipped": result.skipped,
            "errors": result.errors,
            "categories": categories_summary,
            "error_details": result.error_details if result.errors > 0 else []
        }

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"organize_complete: moved={result.moved}, errors={result.errors}"
        )

        logger.info(f"Organization complete: {result.moved} files moved, {result.errors} errors")

        return response

    async def _scan_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan directory and preview organization plan without moving files.

        Args:
            params: Dict with:
                - source: Source directory path
                - patterns: File patterns to match (optional)

        Returns:
            Dict with scan results and organization preview
        """
        source = params.get("source")
        patterns = params.get("patterns", ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp", "*.bmp"])

        if not source:
            return {"status": "error", "error": "Missing 'source' parameter"}

        logger.info(f"Scanning directory: {source}")

        # Scan directory
        files = scan_directory(source, patterns=patterns, recursive=True)

        if not files:
            return {
                "status": "success",
                "message": "No files found matching patterns",
                "files_found": 0
            }

        # Classify images
        logger.info(f"Classifying {len(files)} images...")
        classifications = await self.classifier.classify_batch(files, batch_size=self.batch_size)

        # Build category summary
        categories_summary = {}
        for classification in classifications:
            cat = classification.category
            if cat not in categories_summary:
                categories_summary[cat] = {
                    "count": 0,
                    "avg_confidence": 0.0,
                    "files": []
                }
            categories_summary[cat]["count"] += 1
            categories_summary[cat]["avg_confidence"] += classification.confidence

        # Calculate averages
        for cat, data in categories_summary.items():
            if data["count"] > 0:
                data["avg_confidence"] = data["avg_confidence"] / data["count"]

        # Get sample files for each category (first 3)
        for file_path, classification in zip(files, classifications):
            cat = classification.category
            if len(categories_summary[cat]["files"]) < 3:
                categories_summary[cat]["files"].append({
                    "path": file_path,
                    "confidence": classification.confidence,
                    "reason": classification.reason
                })

        return {
            "status": "success",
            "source": source,
            "files_found": len(files),
            "categories": categories_summary
        }

    async def _get_stats(self) -> Dict[str, Any]:
        """
        Get agent and classification statistics.

        Returns:
            Dict with statistics
        """
        cache_stats = self.classifier.get_cache_stats()

        return {
            "status": "success",
            "agent_stats": self.stats,
            "cache_stats": cache_stats,
            "config": {
                "mode": self.mode,
                "dry_run": self.dry_run,
                "confidence_threshold": self.confidence_threshold,
                "conflict_strategy": self.conflict_strategy,
                "batch_size": self.batch_size
            }
        }

    async def _clear_cache(self) -> Dict[str, Any]:
        """
        Clear classification cache.

        Returns:
            Dict with result
        """
        self.classifier.clear_cache()

        return {
            "status": "success",
            "message": "Classification cache cleared"
        }

    async def on_start(self):
        """Agent startup hook."""
        logger.info(f"FileOrganizerAgent starting...")
        self.session_logger.log_agent_activity(self.agent_id, "started")

    async def on_stop(self):
        """Agent shutdown hook."""
        logger.info(f"FileOrganizerAgent stopping...")

        # Close classifier and cache
        self.classifier.close()

        # Log final statistics
        self.session_logger.log_agent_activity(
            self.agent_id,
            f"stopped: {self.stats}"
        )

        logger.info(f"FileOrganizerAgent stopped. Final stats: {self.stats}")

    async def on_error(self, error: Exception):
        """Error handling hook."""
        logger.error(f"FileOrganizerAgent error: {error}")
        self.session_logger.log_agent_error(self.agent_id, str(error))
        self.stats["errors"] += 1
        await super().on_error(error)


# Convenience function for standalone usage
async def organize_directory(
    source: str,
    dest: Optional[str] = None,
    mode: str = "hybrid",
    dry_run: bool = True,
    conflict_strategy: str = "rename"
) -> Dict[str, Any]:
    """
    Standalone function to organize a directory without agent infrastructure.

    Args:
        source: Source directory path
        dest: Destination directory path (optional, defaults to source)
        mode: Classification mode ("local", "hybrid", "api")
        dry_run: If True, preview only
        conflict_strategy: Conflict resolution strategy

    Returns:
        Dict with organization results
    """
    from src.core.message_bus import MessageBus
    from src.observability.session_logger import SessionLogger

    # Create minimal infrastructure
    bus = MessageBus()
    logger_session = SessionLogger()

    # Create agent
    agent = FileOrganizerAgent(
        message_bus=bus,
        session_logger=logger_session,
        config={
            "mode": mode,
            "dry_run": dry_run,
            "conflict_strategy": conflict_strategy
        }
    )

    await agent.on_start()

    try:
        # Organize directory
        result = await agent._organize_directory({
            "source": source,
            "dest": dest or source,
            "dry_run": dry_run
        })

        return result

    finally:
        await agent.on_stop()
