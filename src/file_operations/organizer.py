"""
File Operations Module for AI-Powered File Organizer.

Provides safe file operations with:
- Rollback support for error recovery
- Duplicate detection and handling
- Permission checking
- Dry-run mode for preview
"""

import hashlib
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FileOperation:
    """Represents a file operation for transaction tracking."""

    operation_type: str  # "move", "copy", "delete"
    source_path: str
    dest_path: Optional[str] = None
    status: str = "pending"  # "pending", "success", "failed", "rolled_back"
    error: Optional[str] = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class OrganizeResult:
    """Result of a file organization operation."""

    total_files: int = 0
    processed: int = 0
    moved: int = 0
    skipped: int = 0
    errors: int = 0
    operations: List[FileOperation] = field(default_factory=list)
    error_details: List[str] = field(default_factory=list)


class FileOrganizer:
    """
    Safe file organizer with transaction support and rollback capabilities.

    Features:
    - Dry-run mode for preview
    - Transaction support with rollback
    - Duplicate detection (hash-based)
    - Conflict resolution strategies
    - Permission checking
    """

    def __init__(
        self,
        dry_run: bool = True,
        conflict_strategy: str = "rename",
        verify_move: bool = True
    ):
        """
        Initialize file organizer.

        Args:
            dry_run: If True, simulate operations without moving files
            conflict_strategy: How to handle conflicts ("skip", "rename", "dedupe", "overwrite")
            verify_move: Verify file integrity after move operations
        """
        if conflict_strategy not in ["skip", "rename", "dedupe", "overwrite"]:
            raise ValueError(f"Invalid conflict_strategy: {conflict_strategy}")

        self.dry_run = dry_run
        self.conflict_strategy = conflict_strategy
        self.verify_move = verify_move
        self.transaction_log: List[FileOperation] = []

        logger.info(f"FileOrganizer initialized (dry_run={dry_run}, conflict={conflict_strategy})")

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file for duplicate detection."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _files_identical(self, path1: str, path2: str) -> bool:
        """Check if two files are identical by comparing hashes."""
        try:
            hash1 = self._compute_file_hash(path1)
            hash2 = self._compute_file_hash(path2)
            return hash1 == hash2
        except Exception as e:
            logger.error(f"Failed to compare files {path1} and {path2}: {e}")
            return False

    def _handle_conflict(self, source: str, dest: str) -> Optional[str]:
        """
        Handle file conflict at destination.

        Args:
            source: Source file path
            dest: Destination file path that already exists

        Returns:
            Modified destination path, or None to skip the operation
        """
        if not os.path.exists(dest):
            return dest

        # Strategy 1: Skip existing files
        if self.conflict_strategy == "skip":
            logger.debug(f"Skipping {source} (destination exists): {dest}")
            return None

        # Strategy 2: Rename with suffix
        elif self.conflict_strategy == "rename":
            base, ext = os.path.splitext(dest)
            counter = 1
            new_dest = dest

            while os.path.exists(new_dest):
                new_dest = f"{base}_{counter}{ext}"
                counter += 1

            logger.debug(f"Renamed destination to avoid conflict: {new_dest}")
            return new_dest

        # Strategy 3: Deduplicate (skip if identical)
        elif self.conflict_strategy == "dedupe":
            if self._files_identical(source, dest):
                logger.debug(f"Skipping duplicate file: {source} (identical to {dest})")
                return None
            else:
                # Files are different, rename
                base, ext = os.path.splitext(dest)
                counter = 1
                new_dest = f"{base}_{counter}{ext}"

                while os.path.exists(new_dest):
                    new_dest = f"{base}_{counter}{ext}"
                    counter += 1

                logger.debug(f"Non-identical file, renamed: {new_dest}")
                return new_dest

        # Strategy 4: Overwrite existing files (dangerous!)
        elif self.conflict_strategy == "overwrite":
            logger.warning(f"Overwriting existing file: {dest}")
            return dest

        return dest

    def _check_permissions(self, source: str, dest_dir: str) -> Tuple[bool, Optional[str]]:
        """
        Check if we have permissions to move file.

        Args:
            source: Source file path
            dest_dir: Destination directory path

        Returns:
            Tuple of (success, error_message)
        """
        # Check source read permission
        if not os.access(source, os.R_OK):
            return False, f"Cannot read source file: {source}"

        # Check if source is actually a file
        if not os.path.isfile(source):
            return False, f"Source is not a file: {source}"

        # Create destination directory if needed (in real mode)
        if not self.dry_run and not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create destination directory: {dest_dir}: {e}"

        # Check destination write permission
        if os.path.exists(dest_dir) and not os.access(dest_dir, os.W_OK):
            return False, f"Cannot write to destination directory: {dest_dir}"

        return True, None

    def move_file(self, source: str, dest: str) -> FileOperation:
        """
        Move a file from source to destination with safety checks.

        Args:
            source: Source file path
            dest: Destination file path

        Returns:
            FileOperation result
        """
        operation = FileOperation(
            operation_type="move",
            source_path=source,
            dest_path=dest
        )

        try:
            # Check permissions
            dest_dir = os.path.dirname(dest)
            can_proceed, error_msg = self._check_permissions(source, dest_dir)

            if not can_proceed:
                operation.status = "failed"
                operation.error = error_msg
                logger.error(error_msg)
                return operation

            # Handle conflicts
            final_dest = self._handle_conflict(source, dest)

            if final_dest is None:
                operation.status = "skipped"
                operation.dest_path = None
                return operation

            operation.dest_path = final_dest

            # Dry-run mode: just log what would happen
            if self.dry_run:
                logger.info(f"[DRY RUN] Would move: {source} -> {final_dest}")
                operation.status = "success"
                return operation

            # Real mode: actually move the file
            # Create destination directory if needed
            os.makedirs(os.path.dirname(final_dest), exist_ok=True)

            # Move the file
            shutil.move(source, final_dest)

            # Verify move if enabled
            if self.verify_move and not os.path.exists(final_dest):
                raise IOError(f"File move verification failed: {final_dest} does not exist")

            operation.status = "success"
            logger.info(f"Moved: {source} -> {final_dest}")

            # Add to transaction log for rollback support
            self.transaction_log.append(operation)

            return operation

        except Exception as e:
            operation.status = "failed"
            operation.error = str(e)
            logger.error(f"Failed to move {source} to {dest}: {e}")
            return operation

    def organize_files(
        self,
        file_mappings: Dict[str, str],
        progress_callback: Optional[callable] = None
    ) -> OrganizeResult:
        """
        Organize multiple files according to mappings.

        Args:
            file_mappings: Dict mapping source paths to destination paths
            progress_callback: Optional callback function(current, total, file_path)

        Returns:
            OrganizeResult with statistics and operation details
        """
        result = OrganizeResult(total_files=len(file_mappings))

        for i, (source, dest) in enumerate(file_mappings.items()):
            # Progress callback
            if progress_callback:
                progress_callback(i + 1, result.total_files, source)

            # Move file
            operation = self.move_file(source, dest)
            result.operations.append(operation)
            result.processed += 1

            # Update stats
            if operation.status == "success":
                result.moved += 1
            elif operation.status == "skipped":
                result.skipped += 1
            elif operation.status == "failed":
                result.errors += 1
                result.error_details.append(f"{source}: {operation.error}")

        return result

    def rollback(self) -> Dict[str, Any]:
        """
        Rollback all operations in the transaction log.

        Returns:
            Dict with rollback statistics
        """
        if self.dry_run:
            logger.info("Rollback called in dry-run mode (nothing to undo)")
            return {"status": "dry_run", "rolled_back": 0}

        rolled_back = 0
        errors = []

        # Reverse the transaction log to undo in reverse order
        for operation in reversed(self.transaction_log):
            if operation.status != "success":
                continue

            try:
                # Only rollback move operations
                if operation.operation_type == "move" and operation.dest_path:
                    # Move file back to original location
                    if os.path.exists(operation.dest_path):
                        shutil.move(operation.dest_path, operation.source_path)
                        operation.status = "rolled_back"
                        rolled_back += 1
                        logger.info(f"Rolled back: {operation.dest_path} -> {operation.source_path}")

            except Exception as e:
                error_msg = f"Failed to rollback {operation.dest_path}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)

        return {
            "status": "completed",
            "rolled_back": rolled_back,
            "errors": errors
        }

    def get_transaction_log(self) -> List[FileOperation]:
        """Get the transaction log of all operations."""
        return self.transaction_log

    def clear_transaction_log(self):
        """Clear the transaction log."""
        self.transaction_log = []
        logger.info("Transaction log cleared")


def scan_directory(
    directory: str,
    patterns: List[str] = None,
    recursive: bool = True,
    exclude_patterns: List[str] = None
) -> List[str]:
    """
    Scan directory for image files matching patterns.

    Args:
        directory: Directory path to scan
        patterns: File patterns to match (e.g., ["*.jpg", "*.png"])
        recursive: Whether to scan subdirectories
        exclude_patterns: Patterns to exclude

    Returns:
        List of matching file paths
    """
    if patterns is None:
        patterns = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp"]

    if exclude_patterns is None:
        exclude_patterns = []

    directory_path = Path(directory)

    if not directory_path.exists():
        logger.error(f"Directory does not exist: {directory}")
        return []

    if not directory_path.is_dir():
        logger.error(f"Path is not a directory: {directory}")
        return []

    matched_files = []

    # Use glob for pattern matching
    for pattern in patterns:
        if recursive:
            matches = directory_path.rglob(pattern)
        else:
            matches = directory_path.glob(pattern)

        for file_path in matches:
            # Skip if matches exclude pattern
            skip = False
            for exclude_pattern in exclude_patterns:
                if file_path.match(exclude_pattern):
                    skip = True
                    break

            if not skip and file_path.is_file():
                matched_files.append(str(file_path.absolute()))

    logger.info(f"Found {len(matched_files)} files in {directory}")
    return matched_files


def create_category_folders(base_dir: str, categories: List[str]) -> Dict[str, str]:
    """
    Create category folders in base directory.

    Args:
        base_dir: Base directory path
        categories: List of category names

    Returns:
        Dict mapping category names to folder paths
    """
    base_path = Path(base_dir)
    category_paths = {}

    for category in categories:
        category_path = base_path / category
        category_paths[category] = str(category_path)

        if not category_path.exists():
            try:
                category_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created category folder: {category_path}")
            except Exception as e:
                logger.error(f"Failed to create category folder {category_path}: {e}")

    return category_paths
