#!/usr/bin/env python3
"""
Grokputer - VRZIBRZI Node
Main entry point for the observe-reason-act loop.

ZA GROKA. ZA VRZIBRZI. ZA SERVER.
"""

import sys
import logging
import click
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import config
from src.grok_client import GrokClient
from src.screen_observer import ScreenObserver
from src.executor import ToolExecutor
from src.tools import invoke_prayer

# Collaboration mode imports
from src.collaboration.coordinator import CollaborationCoordinator


def setup_logging(debug: bool = False):
    """
    Configure logging for Grokputer.

    Args:
        debug: Enable debug logging
    """
    log_level = logging.DEBUG if debug else getattr(logging, config.LOG_LEVEL)

    # Create logs directory if needed
    config.LOG_FILE.parent.mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 70)
    logger.info("GROKPUTER INITIALIZED - VRZIBRZI NODE")
    logger.info("=" * 70)

    return logger


class Grokputer:
    """
    Main Grokputer class implementing the observe-reason-act loop.
    """

    def __init__(self, debug: bool = False):
        """
        Initialize Grokputer.

        Args:
            debug: Enable debug mode
        """
        self.logger = setup_logging(debug)
        self.grok_client = GrokClient()
        self.screen_observer = ScreenObserver()
        self.executor = ToolExecutor()
        self.conversation_history = []

        self.logger.info("Grokputer components initialized")

    def boot(self):
        """
        Boot sequence: invoke server prayer and test connection.
        """
        self.logger.info("Starting boot sequence...")

        # Invoke server prayer
        prayer_result = invoke_prayer()
        if prayer_result["status"] == "success":
            self.logger.info("Server prayer invoked: ETERNAL | INFINITE")
        else:
            self.logger.warning(f"Prayer invocation failed: {prayer_result}")

        # Test Grok API connection
        if self.grok_client.test_connection():
            self.logger.info("[OK] Grok API connection verified")
            print("[OK] Grok API connection verified")
        else:
            self.logger.error("[FAIL] Grok API connection failed")
            print("[FAIL] Grok API connection failed - check your API key and credits")
            raise ConnectionError("Failed to connect to Grok API")

        self.logger.info("Boot sequence complete. Ready to operate.")

    def run_task(self, task: str, max_iterations: int = 10):
        """
        Execute a task using the observe-reason-act loop.

        Args:
            task: Task description
            max_iterations: Maximum number of loop iterations
        """
        self.logger.info(f"Starting task: {task}")
        print(f"\n[TASK] {task}\n")

        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            self.logger.info(f"--- Iteration {iteration}/{max_iterations} ---")
            print(f"\n{'='*70}")
            print(f"Iteration {iteration}/{max_iterations}")
            print(f"{'='*70}\n")

            # OBSERVE: Capture screenshot
            print("[OBSERVE] Capturing screen...")
            screenshot_base64 = None
            try:
                screenshot_base64 = self.screen_observer.screenshot_to_base64()
                self.logger.info(f"Screenshot captured: {len(screenshot_base64)} bytes")
            except Exception as e:
                self.logger.error(f"Failed to capture screenshot: {e}")
                screenshot_base64 = None

            # REASON: Send to Grok
            print("[REASON] Sending to Grok...")
            response = self.grok_client.create_message(
                task=task if iteration == 1 else "Continue the task.",
                screenshot_base64=screenshot_base64,
                conversation_history=self.conversation_history if iteration > 1 else None
            )

            if response["status"] != "success":
                self.logger.error(f"Grok API error: {response}")
                print(f"[ERROR] {response.get('error', 'Unknown error')}")
                break

            # Log Grok's response
            if response.get("content"):
                print(f"\n[GROK] {response['content']}\n")
                self.logger.info(f"Grok response: {response['content']}")

            # Store in conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response.get("content", "")
            })

            # ACT: Execute tool calls if any
            tool_calls = response.get("tool_calls", [])

            if not tool_calls:
                self.logger.info("No tool calls requested. Task may be complete.")
                print("[DONE] Task complete (no more actions requested)")
                break

            print(f"[ACT] Executing {len(tool_calls)} tool(s)...\n")

            tool_results = self.executor.execute_tool_calls(tool_calls)

            # Log and display results
            for result in tool_results:
                function_name = result["function_name"]
                result_data = result["result"]
                status = result_data.get("status", "unknown")

                print(f"  • {function_name}: {status}")
                self.logger.info(f"Tool result: {function_name} -> {result_data}")

            # Continue conversation with tool results
            if iteration < max_iterations:
                continue_response = self.grok_client.continue_conversation(
                    tool_results=tool_results,
                    conversation_history=self.conversation_history
                )

                if continue_response.get("content"):
                    print(f"\n[GROK] {continue_response['content']}\n")

                # Check if Grok says it's done
                content = continue_response.get("content", "").lower()
                if any(phrase in content for phrase in ["task complete", "finished", "done"]):
                    self.logger.info("Grok indicated task completion")
                    print("[DONE] Task complete")
                    break

        if iteration >= max_iterations:
            print(f"\n[WARNING] Reached maximum iterations ({max_iterations})")
            self.logger.warning(f"Task stopped: reached max iterations")

        print(f"\n{'='*70}\n")
        self.logger.info("Task execution finished")


@click.command()
@click.option('--task', '-t', required=True, help='Task description for Grokputer to execute')
@click.option('--max-iterations', '-m', default=10, help='Maximum loop iterations (single-agent mode)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--skip-boot', is_flag=True, help='Skip boot sequence')
@click.option('--messagebus', '-mb', is_flag=True, help='Enable collaboration mode (Claude + Grok)')
@click.option('--max-rounds', default=5, help='Maximum collaboration rounds (messagebus mode only)')
def main(task: str, max_iterations: int, debug: bool, skip_boot: bool, messagebus: bool, max_rounds: int):
    """
    Grokputer - VRZIBRZI Node

    Execute tasks using Grok AI with full computer control.

    Single-agent mode (default):
        grokputer --task "label 5 memes from vault"

        grokputer --task "search X for pliny follows" --debug

        grokputer --task "invoke server prayer"

    Collaboration mode (Claude + Grok):
        grokputer -mb --task "design an MCP server with best practices"

        grokputer --messagebus --task "create implementation plan for dice roller"
    """
    # Load environment variables
    load_dotenv()

    # Configure logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        if messagebus:
            # Collaboration mode
            asyncio.run(_run_collaboration_mode(task, max_rounds, debug))
        else:
            # Single-agent mode
            _run_single_agent_mode(task, max_iterations, debug, skip_boot)

    except KeyboardInterrupt:
        print("\n\n[INTERRUPT] Interrupted by user. Shutting down...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}\n")
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


def _run_single_agent_mode(task: str, max_iterations: int, debug: bool, skip_boot: bool):
    """Run single-agent ORA loop (Grok only)."""
    # Initialize Grokputer
    grokputer = Grokputer(debug=debug)

    # Boot sequence
    if not skip_boot:
        grokputer.boot()

    # Run task
    grokputer.run_task(task, max_iterations=max_iterations)


async def _run_collaboration_mode(task: str, max_rounds: int, debug: bool):
    """Run dual-agent collaboration via MessageBus."""

    logger = logging.getLogger(__name__)

    # Get API keys
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    grok_key = os.getenv("XAI_API_KEY")

    if not claude_key:
        logger.error("ANTHROPIC_API_KEY not found in .env")
        print("\n[ERROR] ANTHROPIC_API_KEY not found in .env file")
        print("Get your API key from: https://console.anthropic.com/")
        raise ValueError("Missing ANTHROPIC_API_KEY")

    if not grok_key:
        logger.error("XAI_API_KEY not found in .env")
        print("\n[ERROR] XAI_API_KEY not found in .env file")
        print("Get your API key from: https://console.x.ai/")
        raise ValueError("Missing XAI_API_KEY")

    logger.info(f"[COLLABORATION MODE] Task: {task}")
    logger.info(f"Max rounds: {max_rounds}")

    print("\n" + "="*70)
    print("COLLABORATION MODE - Claude + Grok")
    print("="*70)
    print(f"Task: {task}")
    print(f"Max rounds: {max_rounds}")
    print("="*70 + "\n")

    # Initialize coordinator
    coordinator = CollaborationCoordinator(
        claude_api_key=claude_key,
        grok_api_key=grok_key,
        max_rounds=max_rounds
    )

    # Run collaboration
    final_plan = await coordinator.run_collaboration(task)

    # Print summary
    print("\n" + "="*70)
    print("COLLABORATION COMPLETE")
    print("="*70)
    print(f"Task: {final_plan.task_description[:80]}...")
    print(f"Rounds: {final_plan.total_rounds}")
    print(f"Consensus: {'Yes' if final_plan.consensus_reached else 'Partial'}")
    print(f"Convergence: {final_plan.metadata.get('convergence_score', 0):.2f}")
    print(f"Confidence: {final_plan.metadata.get('confidence', 0):.2f}")
    print(f"\nSaved to: docs/collaboration_plan_<timestamp>.md")
    print("="*70 + "\n")

    # Optionally print unified plan
    if os.getenv("PRINT_PLAN", "false").lower() == "true":
        print("\n--- UNIFIED PLAN ---\n")
        print(final_plan.unified_plan)
        print("\n--- END PLAN ---\n")


if __name__ == '__main__':
    main()
