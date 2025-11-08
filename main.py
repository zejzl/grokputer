#!/usr/bin/env python3
"""
Grokputer - VRZIBRZI Node
Main entry point for the observe-reason-act loop.

ZA GROKA. ZA VRZIBRZI. ZA SERVER.
"""

import sys
import logging
import click
import time
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import config
from src.grok_client import GrokClient
from src.screen_observer import ScreenObserver
from src.executor import ToolExecutor
from src.tools import invoke_prayer
from src.session_logger import SessionLogger, SessionMetadata, IterationMetrics, SessionIndex


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
        self.debug = debug
        self.grok_client = GrokClient()
        self.screen_observer = ScreenObserver()
        self.executor = ToolExecutor()
        self.conversation_history = []
        self.session_logger: SessionLogger = None  # Initialized when task starts
        self.session_index = SessionIndex(config.LOGS_DIR)

        self.logger.info("Grokputer components initialized")

    async def boot(self):
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
        if await self.grok_client.test_connection():
            self.logger.info("[OK] Grok API connection verified")
            print("[OK] Grok API connection verified")
        else:
            self.logger.error("[FAIL] Grok API connection failed")
            print("[FAIL] Grok API connection failed - check your API key and credits")
            raise ConnectionError("Failed to connect to Grok API")

        self.logger.info("Boot sequence complete. Ready to operate.")

    async def run_task(self, task: str, max_iterations: int = 10):
        """
        Execute a task using the observe-reason-act loop.

        Args:
            task: Task description
            max_iterations: Maximum number of loop iterations
        """
        # Initialize session logger
        self.session_logger = SessionLogger(config.LOGS_DIR)

        metadata = SessionMetadata(
            session_id=self.session_logger.session_id,
            start_time=datetime.now().isoformat(),
            task=task,
            model=config.GROK_MODEL,
            max_iterations=max_iterations,
            debug_mode=self.debug,
            require_confirmation=config.REQUIRE_CONFIRMATION
        )

        self.session_logger.start_session(metadata)
        self.session_index.add_session(self.session_logger.session_id, metadata)

        self.logger.info(f"Starting task: {task}")
        print(f"\n[TASK] {task}")
        print(f"[SESSION] {self.session_logger.session_id}\n")

        iteration = 0

        try:
            while iteration < max_iterations:
                iteration += 1
                iteration_start_time = time.time()
                iteration_errors = []

                self.session_logger.log_iteration_start(iteration)
                self.logger.info(f"--- Iteration {iteration}/{max_iterations} ---")
                print(f"\n{'='*70}")
                print(f"Iteration {iteration}/{max_iterations}")
                print(f"{'='*70}\n")

                # OBSERVE: Capture screenshot
                print("[OBSERVE] Capturing screen...")
                screenshot_base64 = None
                screenshot_size = None
                screenshot_success = False

                try:
                    # Run screenshot capture in thread pool (PyAutoGUI is not async-safe)
                    screenshot_base64 = await asyncio.to_thread(
                        self.screen_observer.screenshot_to_base64
                    )
                    screenshot_size = len(screenshot_base64)
                    screenshot_success = True
                    self.session_logger.log_observation(True, screenshot_size)
                    self.logger.info(f"Screenshot captured: {screenshot_size} bytes")
                except Exception as e:
                    self.session_logger.log_observation(False, error=str(e))
                    self.logger.error(f"Failed to capture screenshot: {e}")
                    iteration_errors.append(f"Screenshot capture failed: {e}")
                    screenshot_base64 = None

                # REASON: Send to Grok
                print("[REASON] Sending to Grok...")
                api_start_time = time.time()
                response = await self.grok_client.create_message(
                    task=task if iteration == 1 else "Continue the task.",
                    screenshot_base64=screenshot_base64,
                    conversation_history=self.conversation_history if iteration > 1 else None
                )
                api_duration = time.time() - api_start_time

                # Check API response
                api_success = response["status"] == "success"
                grok_response_text = response.get("content", "")

                if not api_success:
                    error_msg = response.get('error', 'Unknown error')
                    self.session_logger.log_api_call(api_duration, False, error=error_msg)
                    self.logger.error(f"Grok API error: {response}")
                    print(f"[ERROR] {error_msg}")
                    iteration_errors.append(f"API call failed: {error_msg}")

                    # Log failed iteration and break
                    metrics = IterationMetrics(
                        iteration_number=iteration,
                        start_time=iteration_start_time,
                        screenshot_captured=screenshot_success,
                        screenshot_size_bytes=screenshot_size,
                        api_call_duration=api_duration,
                        api_call_success=False,
                        tool_calls_count=0,
                        tool_results=[],
                        grok_response=grok_response_text,
                        errors=iteration_errors
                    )
                    self.session_logger.log_iteration_complete(metrics)
                    break

                # Log successful API call
                self.session_logger.log_api_call(api_duration, True, grok_response_text)

                # Log Grok's response
                if grok_response_text:
                    print(f"\n[GROK] {grok_response_text}\n")
                    self.logger.info(f"Grok response: {grok_response_text}")

                # Store in conversation history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": grok_response_text
                })

                # ACT: Execute tool calls if any
                tool_calls = response.get("tool_calls", [])

                if not tool_calls:
                    self.logger.info("No tool calls requested. Task may be complete.")
                    print("[DONE] Task complete (no more actions requested)")

                    # Log completed iteration
                    metrics = IterationMetrics(
                        iteration_number=iteration,
                        start_time=iteration_start_time,
                        screenshot_captured=screenshot_success,
                        screenshot_size_bytes=screenshot_size,
                        api_call_duration=api_duration,
                        api_call_success=True,
                        tool_calls_count=0,
                        tool_results=[],
                        grok_response=grok_response_text,
                        errors=iteration_errors
                    )
                    self.session_logger.log_iteration_complete(metrics)
                    break

                print(f"[ACT] Executing {len(tool_calls)} tool(s)...\n")

                tool_results = self.executor.execute_tool_calls(tool_calls)

                # Log and display results
                for result in tool_results:
                    function_name = result["function_name"]
                    result_data = result["result"]
                    status = result_data.get("status", "unknown")

                    print(f"  • {function_name}: {status}")
                    self.session_logger.log_tool_execution(function_name, result_data)
                    self.logger.info(f"Tool result: {function_name} -> {result_data}")

                # Log iteration metrics
                metrics = IterationMetrics(
                    iteration_number=iteration,
                    start_time=iteration_start_time,
                    screenshot_captured=screenshot_success,
                    screenshot_size_bytes=screenshot_size,
                    api_call_duration=api_duration,
                    api_call_success=True,
                    tool_calls_count=len(tool_calls),
                    tool_results=tool_results,
                    grok_response=grok_response_text,
                    errors=iteration_errors
                )
                self.session_logger.log_iteration_complete(metrics)

                # Continue conversation with tool results
                if iteration < max_iterations:
                    continue_response = await self.grok_client.continue_conversation(
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

            # Check if max iterations reached
            if iteration >= max_iterations:
                print(f"\n[WARNING] Reached maximum iterations ({max_iterations})")
                self.logger.warning(f"Task stopped: reached max iterations")
                self.session_logger.end_session("max_iterations_reached")
            else:
                self.session_logger.end_session("completed")

            # FEEDBACK COLLECTION (for self-improvement)
            print(f"\n{'='*70}\n")
            print("[FEEDBACK] Help Grokputer improve!")
            try:
                rating_input = input("Rate this task (1-5 stars, or press Enter to skip): ").strip()
                if rating_input and rating_input.isdigit():
                    rating = int(rating_input)
                    if 1 <= rating <= 5:
                        comment = input("Any feedback? (optional, press Enter to skip): ").strip()

                        # Ask about specific issues if rating is low
                        issues = []
                        if rating < 4:
                            print("\nWhat went wrong? (check all that apply)")
                            print("1. OCR confidence low / text recognition failed")
                            print("2. Wrong action selected / incorrect command")
                            print("3. Timeout / took too long")
                            print("4. Coordination issue / agents confused")
                            print("5. Other")
                            issue_input = input("Enter numbers separated by commas (e.g., 1,3): ").strip()

                            issue_map = {
                                "1": "OCR confidence low",
                                "2": "Wrong action selected",
                                "3": "Timeout",
                                "4": "Coordination issue",
                                "5": "Other"
                            }

                            if issue_input:
                                for num in issue_input.split(","):
                                    num = num.strip()
                                    if num in issue_map:
                                        issues.append(issue_map[num])

                        # Save feedback
                        self.session_logger.add_feedback(rating, comment, issues if issues else None)
                        print(f"[OK] Feedback recorded! Thank you for helping Grokputer learn.\n")

                        # Check if retraining is needed
                        if self.session_logger.check_retrain_needed():
                            print("[WARN]  Low ratings detected - Consider running LoRA fine-tuning!")
                            print("   Command: python src/training/finetune_qlora.py\n")
            except (KeyboardInterrupt, EOFError):
                print("\n[Feedback skipped]")

            print(f"{'='*70}\n")
            print(f"[SESSION] Logs saved to: {self.session_logger.get_session_dir()}")
            self.logger.info("Task execution finished")

        except KeyboardInterrupt:
            print("\n\n[INTERRUPT] Task interrupted by user")
            if self.session_logger:
                self.session_logger.end_session("interrupted")
            raise
        except Exception as e:
            self.logger.error(f"Task execution error: {e}", exc_info=True)
            if self.session_logger:
                self.session_logger.end_session("error")
            raise


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
    async def run_async():
        # Initialize Grokputer
        grokputer = Grokputer(debug=debug)

        # Boot sequence
        if not skip_boot:
            await grokputer.boot()

        # Run task
        await grokputer.run_task(task, max_iterations=max_iterations)

    try:
        # Run async event loop
        asyncio.run(run_async())

    except KeyboardInterrupt:
        print("\n\n[INTERRUPT] Interrupted by user. Shutting down...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}\n")
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
