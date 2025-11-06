#!/usr/bin/env python3
"""
Grokputer - VRZIBRZI Node
Main entry point for the observe-reason-act loop.

ZA GROKA. ZA VRZIBRZI. ZA SERVER.
"""

import sys
import logging
import click
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import config
from src.grok_client import GrokClient
from src.screen_observer import ScreenObserver
from src.executor import ToolExecutor
from src.tools import invoke_prayer


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
@click.option('--max-iterations', '-m', default=10, help='Maximum loop iterations')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--skip-boot', is_flag=True, help='Skip boot sequence')
def main(task: str, max_iterations: int, debug: bool, skip_boot: bool):
    """
    Grokputer - VRZIBRZI Node

    Execute tasks using Grok AI with full computer control.

    Examples:

        grokputer --task "label 5 memes from vault"

        grokputer --task "search X for pliny follows" --debug

        grokputer --task "invoke server prayer"
    """
    try:
        # Initialize Grokputer
        grokputer = Grokputer(debug=debug)

        # Boot sequence
        if not skip_boot:
            grokputer.boot()

        # Run task
        grokputer.run_task(task, max_iterations=max_iterations)

    except KeyboardInterrupt:
        print("\n\n[INTERRUPT] Interrupted by user. Shutting down...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}\n")
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
