#!/usr/bin/env python3
"""
AI-Powered File Organizer CLI for Grokputer.

Command-line interface for organizing image files using vision AI.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Import organizer components
from src.agents.file_organizer_agent import organize_directory
from src.file_operations.organizer import scan_directory
from src.vision.image_classifier import ImageClassifier


def load_config(config_path: Optional[str] = None, preset: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file (None for default)
        preset: Preset name to apply (None for default)

    Returns:
        Config dict
    """
    if config_path is None:
        config_path = "config/organizer_config.yaml"

    config_file = Path(config_path)

    if not config_file.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return {}

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    # Apply preset if specified
    if preset and "presets" in config and preset in config["presets"]:
        logger.info(f"Applying preset: {preset}")
        config.update(config["presets"][preset])

    return config


def print_banner():
    """Print CLI banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     GROKPUTER FILE ORGANIZER                                  ║
║     AI-Powered Image Classification & Organization           ║
║                                                               ║
║     ZA GROKA. ZA VRZIBRZI. ZA FILE ORGANIZATION.             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    click.echo(click.style(banner, fg="cyan", bold=True))


def print_summary(result: Dict[str, Any]):
    """Print organization summary."""
    click.echo("\n" + "=" * 60)
    click.echo(click.style("ORGANIZATION SUMMARY", fg="green", bold=True))
    click.echo("=" * 60)

    # Basic stats
    click.echo(f"\nFiles found:      {result.get('files_found', 0)}")
    click.echo(f"Files processed:  {result.get('files_processed', 0)}")

    if result.get('dry_run'):
        click.echo(click.style("\n[DRY RUN MODE]", fg="yellow", bold=True))
        click.echo("No files were actually moved. Run with --execute to apply changes.")
        click.echo(f"\nWould move:       {result.get('files_moved', 0)} files")
    else:
        click.echo(click.style("\n[EXECUTE MODE]", fg="red", bold=True))
        click.echo(f"\nFiles moved:      {result.get('files_moved', 0)}")

    click.echo(f"Files skipped:    {result.get('files_skipped', 0)}")
    click.echo(f"Errors:           {result.get('errors', 0)}")

    # Categories breakdown
    categories = result.get('categories', {})
    if categories:
        click.echo("\n" + "-" * 60)
        click.echo(click.style("CATEGORIES", fg="cyan", bold=True))
        click.echo("-" * 60)

        for category, data in sorted(categories.items(), key=lambda x: x[1]['count'], reverse=True):
            count = data.get('count', 0)
            confidence = data.get('avg_confidence', 0.0)
            click.echo(f"{category:15} {count:5} files  (avg confidence: {confidence:.2f})")

    # Errors
    errors = result.get('error_details', [])
    if errors:
        click.echo("\n" + "-" * 60)
        click.echo(click.style("ERRORS", fg="red", bold=True))
        click.echo("-" * 60)
        for error in errors[:10]:  # Show first 10 errors
            click.echo(f"  • {error}")
        if len(errors) > 10:
            click.echo(f"  ... and {len(errors) - 10} more errors")

    click.echo("\n" + "=" * 60 + "\n")


@click.group()
def cli():
    """AI-Powered File Organizer for Grokputer."""
    pass


@cli.command()
@click.option("--source", "-s", required=True, help="Source directory to organize")
@click.option("--dest", "-d", default=None, help="Destination directory (default: same as source)")
@click.option("--mode", "-m", type=click.Choice(["local", "hybrid", "api"]), default=None,
              help="Classification mode (local/hybrid/api)")
@click.option("--dry-run", is_flag=True, default=None, help="Preview only, don't move files")
@click.option("--execute", is_flag=True, help="Actually move files (overrides dry-run)")
@click.option("--conflict", type=click.Choice(["skip", "rename", "dedupe", "overwrite"]), default=None,
              help="Conflict resolution strategy")
@click.option("--preset", type=click.Choice(["safe", "balanced", "aggressive", "fast"]),
              help="Use configuration preset")
@click.option("--config", default=None, help="Path to config file")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def organize(source, dest, mode, dry_run, execute, conflict, preset, config, verbose):
    """
    Organize images in a directory using AI classification.

    Examples:

    # Preview organization (dry-run by default)
    python src/file_organizer_main.py organize --source ~/Downloads

    # Actually organize files
    python src/file_organizer_main.py organize --source ~/Downloads --execute

    # Use specific mode and destination
    python src/file_organizer_main.py organize -s ~/Downloads -d ~/Pictures/Organized -m hybrid --execute

    # Use preset configuration
    python src/file_organizer_main.py organize -s ~/Downloads --preset balanced --execute
    """
    print_banner()

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config
    cfg = load_config(config, preset)

    # Override with CLI args
    if mode:
        cfg["mode"] = mode
    if conflict:
        cfg["conflict_strategy"] = conflict

    # Handle dry-run / execute
    if execute:
        cfg["dry_run"] = False
    elif dry_run is not None:
        cfg["dry_run"] = dry_run
    elif "dry_run" not in cfg:
        cfg["dry_run"] = True  # Default to dry-run for safety

    # Set defaults
    cfg.setdefault("mode", "hybrid")
    cfg.setdefault("conflict_strategy", "rename")

    click.echo(f"\nSource:      {source}")
    click.echo(f"Destination: {dest or source}")
    click.echo(f"Mode:        {cfg['mode']}")
    click.echo(f"Conflicts:   {cfg['conflict_strategy']}")
    click.echo(f"Dry-run:     {cfg['dry_run']}")
    click.echo()

    if not cfg["dry_run"]:
        click.echo(click.style("WARNING: Files will be moved! Use Ctrl+C to cancel.", fg="red", bold=True))
        click.echo("Starting in 3 seconds...")
        import time
        for i in range(3, 0, -1):
            click.echo(f"  {i}...")
            time.sleep(1)
        click.echo()

    # Run organization
    click.echo("Starting organization...\n")

    try:
        result = asyncio.run(organize_directory(
            source=source,
            dest=dest,
            mode=cfg["mode"],
            dry_run=cfg["dry_run"],
            conflict_strategy=cfg["conflict_strategy"]
        ))

        # Print summary
        print_summary(result)

        if result.get("status") == "success":
            if result.get("errors", 0) == 0:
                click.echo(click.style("✓ Organization completed successfully!", fg="green", bold=True))
            else:
                click.echo(click.style(f"⚠ Completed with {result['errors']} errors", fg="yellow", bold=True))
            sys.exit(0)
        else:
            click.echo(click.style(f"✗ Organization failed: {result.get('error', 'Unknown error')}", fg="red", bold=True))
            sys.exit(1)

    except KeyboardInterrupt:
        click.echo(click.style("\n\n✗ Cancelled by user", fg="yellow"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg="red", bold=True))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--source", "-s", required=True, help="Directory to scan")
@click.option("--config", default=None, help="Path to config file")
def scan(source, config):
    """
    Scan directory and preview organization plan without moving files.

    Example:
    python src/file_organizer_main.py scan --source ~/Downloads
    """
    print_banner()

    click.echo(f"Scanning directory: {source}\n")

    # Load config
    cfg = load_config(config)

    # Import components
    from src.agents.file_organizer_agent import FileOrganizerAgent
    from src.core.message_bus import MessageBus
    from src.observability.session_logger import SessionLogger

    # Create agent
    bus = MessageBus()
    session_logger = SessionLogger()
    agent = FileOrganizerAgent(bus, session_logger, cfg)

    async def run_scan():
        await agent.on_start()
        try:
            result = await agent._scan_directory({"source": source})
            return result
        finally:
            await agent.on_stop()

    try:
        result = asyncio.run(run_scan())

        if result.get("status") == "success":
            click.echo(f"Files found: {result.get('files_found', 0)}\n")

            categories = result.get('categories', {})
            if categories:
                click.echo(click.style("ORGANIZATION PREVIEW", fg="cyan", bold=True))
                click.echo("-" * 60)

                for category, data in sorted(categories.items(), key=lambda x: x[1]['count'], reverse=True):
                    count = data.get('count', 0)
                    confidence = data.get('avg_confidence', 0.0)
                    click.echo(f"\n{click.style(category.upper(), fg='green', bold=True)}")
                    click.echo(f"  Count: {count} files")
                    click.echo(f"  Avg Confidence: {confidence:.2f}")

                    # Show sample files
                    files = data.get('files', [])
                    if files:
                        click.echo(f"  Samples:")
                        for file_info in files:
                            path = Path(file_info['path']).name
                            conf = file_info['confidence']
                            click.echo(f"    • {path} ({conf:.2f})")

            click.echo(f"\n{click.style('✓ Scan complete!', fg='green', bold=True)}")
            click.echo("Run 'organize --execute' to apply changes.")

        else:
            click.echo(click.style(f"✗ Scan failed: {result.get('error', 'Unknown error')}", fg="red"))
            sys.exit(1)

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--config", default=None, help="Path to config file")
def stats(config):
    """
    Show classification cache statistics.

    Example:
    python src/file_organizer_main.py stats
    """
    print_banner()

    # Load config
    cfg = load_config(config)

    # Create classifier to access cache
    classifier = ImageClassifier(mode=cfg.get("mode", "hybrid"))

    stats_data = classifier.get_cache_stats()

    click.echo(click.style("CACHE STATISTICS", fg="cyan", bold=True))
    click.echo("-" * 60)
    click.echo(f"Total cached: {stats_data.get('total', 0)} images")

    by_category = stats_data.get('by_category', {})
    if by_category:
        click.echo("\nBy category:")
        for category, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
            click.echo(f"  {category:15} {count:5} images")

    classifier.close()


@cli.command()
@click.option("--config", default=None, help="Path to config file")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def clear_cache(config, yes):
    """
    Clear classification cache.

    Example:
    python src/file_organizer_main.py clear-cache --yes
    """
    if not yes:
        if not click.confirm("Are you sure you want to clear the cache?"):
            click.echo("Cancelled.")
            return

    # Load config
    cfg = load_config(config)

    # Create classifier to access cache
    classifier = ImageClassifier(mode=cfg.get("mode", "hybrid"))
    classifier.clear_cache()
    classifier.close()

    click.echo(click.style("✓ Cache cleared successfully!", fg="green"))


@cli.command()
def version():
    """Show version information."""
    click.echo("Grokputer File Organizer v1.0.0")
    click.echo("AI-Powered Image Classification & Organization")
    click.echo("\nZA GROKA. ZA VRZIBRZI. ZA FILE ORGANIZATION.")


if __name__ == "__main__":
    cli()
