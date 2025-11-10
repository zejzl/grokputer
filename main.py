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
from src.tools import code_generator, execute_script

# Collaboration mode imports
from src.collaboration.coordinator import CollaborationCoordinator

# Swarm mode imports
from src.core.message_bus import MessageBus
from src.core.action_executor import ActionExecutor
from src.observability.deadlock_detector import DeadlockDetector
from src.observability.session_logger import SessionLogger
from datetime import datetime

from typing import Optional
from pathlib import Path
import ast
import sys


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
        print("""
[GROKPUTER] BOOTING - VRZIBRZI NODE
""")
        self.logger.info("Grokputer booted with banner")

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


def _run_interactive_mode(debug: bool, max_iterations: int, max_rounds: int, skip_boot: bool):
    """
    Run interactive menu mode - user selects mode and enters task.
    """
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     ██████╗ ██████╗  ██████╗ ██╗  ██╗██████╗ ██╗   ██╗████████╗ ║
║    ██╔════╝ ██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗██║   ██║╚══██╔══╝ ║
║    ██║  ███╗██████╔╝██║   ██║█████╔╝ ██████╔╝██║   ██║   ██║    ║
║    ██║   ██║██╔══██╗██║   ██║██╔═██╗ ██╔═══╝ ██║   ██║   ██║    ║
║    ╚██████╔╝██║  ██║╚██████╔╝██║  ██╗██║     ╚██████╔╝   ██║    ║
║     ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝      ╚═════╝    ╚═╝    ║
║                                                                   ║
║                    VRZIBRZI NODE - INITIALIZED                   ║
║                 ZA GROKA. ZA VRZIBRZI. ZA SERVER.                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

        [INTERACTIVE MODE] Welcome to Grokputer - Choose your agent mode!

        1. Single Agent (Grok only) - Observe-Reason-Act loop
        2. Collaboration Mode (Grok + Claude) - Dual AI planning
        3. Swarm Mode (Multi-agent) - Async team coordination
        4. Improver Manual - Run self-improvement on specific session/log
        5. Offline Mode - Cached/local fallback (no API, uses vault/KB)
        6. Community Vault Sync - Pull/push evolutions and tools
        7. Save Game - Invoke progress save script
        8. Quit

""")

    choice = input("        Choose mode (1-8): ").strip()

    if choice == "1":
        # Single Agent Mode
        print("\n[MODE] Single Agent (Grok only)\n")
        task = input("Enter task: ").strip()
        if task:
            grokputer = Grokputer(debug=debug)
            if not skip_boot:
                grokputer.boot()
            grokputer.run(task=task, max_iterations=max_iterations)
        else:
            print("[ERROR] Task cannot be empty")

    elif choice == "2":
        # Collaboration Mode
        print("\n[MODE] Collaboration Mode (Grok + Claude)\n")
        task = input("Enter task: ").strip()
        if task:
            asyncio.run(_run_collaboration_mode(task, max_rounds, debug, review_mode=False))
        else:
            print("[ERROR] Task cannot be empty")

    elif choice == "3":
        # Swarm Mode
        print("\n[MODE] Swarm Mode (Multi-agent)\n")
        task = input("Enter task: ").strip()
        agent_roles_input = input("Agent roles (default: coordinator,observer,actor): ").strip()
        roles = [r.strip() for r in agent_roles_input.split(',')] if agent_roles_input else ['coordinator', 'observer', 'actor']
        if task:
            asyncio.run(_run_swarm_mode(task, roles, debug))
        else:
            print("[ERROR] Task cannot be empty")

    elif choice == "4":
        # Improver Manual
        print("\n[MODE] Improver Manual - Self-improvement on session/log\n")
        print("[INFO] Improver agent will analyze a specific session and propose improvements")
        session_id = input("Enter session ID (or 'latest'): ").strip()
        if not session_id:
            session_id = "latest"

        try:
            from src.agents.session_improver import SessionImprover
            improver = SessionImprover()
            improver.improve_session(session_id)
        except Exception as e:
            print(f"[ERROR] Improver failed: {e}")
            logging.error(f"Improver error: {e}", exc_info=True)

    elif choice == "5":
        # Offline Mode
        print("\n[MODE] Offline Mode - Cached/local fallback\n")
        print("[INFO] Using cached responses and local knowledge base")
        task = input("Enter task: ").strip()
        if task:
            try:
                from src.offline_mode import run_offline_mode
                run_offline_mode(task, max_iterations)
            except Exception as e:
                print(f"[ERROR] Offline mode failed: {e}")
                logging.error(f"Offline mode error: {e}", exc_info=True)
        else:
            print("[ERROR] Task cannot be empty")

    elif choice == "6":
        # Community Vault Sync
        print("\n[MODE] Community Vault Sync - Pull/push evolutions and tools\n")
        sync_choice = input("Sync action (pull/push/both/list): ").strip().lower()
        if sync_choice in ['pull', 'push', 'both', 'list']:
            try:
                from src.vault_sync import run_vault_sync
                run_vault_sync(sync_choice)
            except Exception as e:
                print(f"[ERROR] Vault sync failed: {e}")
                logging.error(f"Vault sync error: {e}", exc_info=True)
        else:
            print("[ERROR] Invalid sync action. Choose 'pull', 'push', 'both', or 'list'")

    elif choice == "7":
        # Save Game
        print("\n[MODE] Save Game - Invoke progress save script\n")
        print("[SAVE] Creating backup of current state...")
        try:
            import subprocess
            result = subprocess.run(['python', 'outputs/gp_save_progress.py'],
                                  capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print("[SAVE] ✓ Progress saved successfully!")
                print(result.stdout)
            else:
                print(f"[SAVE] ✗ Save failed: {result.stderr}")
        except Exception as e:
            print(f"[SAVE] ✗ Error: {e}")

    elif choice == "8":
        # Quit
        print("\n[EXIT] Za Groka. Za Vrzibrzi. Za Server.\n")
        sys.exit(0)

    else:
        print("\n[ERROR] Invalid choice. Please select 1-8.\n")
        _run_interactive_mode(debug, max_iterations, max_rounds, skip_boot)


@click.command()
@click.option('--task', '-t', default=None, help='Task description for Grokputer to execute (optional: omit for interactive idle mode)')
@click.option('--max-iterations', '-m', default=5, help='Maximum loop iterations (single-agent mode)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--skip-boot', is_flag=True, help='Skip boot sequence')
@click.option('--messagebus', '-mb', is_flag=True, help='Enable collaboration mode (Claude + Grok)')
@click.option('--max-rounds', default=5, help='Maximum collaboration rounds (messagebus mode only)')
@click.option('--review-mode', '-r', is_flag=True, help='Pause after each round for human review (messagebus mode only)')
@click.option('--swarm', is_flag=True, help='Enable multi-agent swarm mode')
@click.option('--agents', default=3, help='Number of agents in swarm (default: 3)')
@click.option('--agent-roles', default='coordinator,observer,actor', help='Comma-separated agent roles')
def main(task: str, max_iterations: int, debug: bool, skip_boot: bool, messagebus: bool, max_rounds: int, review_mode: bool, swarm: bool, agents: int, agent_roles: str, syntax_check: bool = False):
    """
    Grokputer - VRZIBRZI Node

    Execute tasks using Grok AI with full computer control.

    Single-agent mode (default):
        grokputer --task "label 5 memes from vault"

        grokputer  # Interactive menu: Choose mode (single, collab, swarm) and enter task

        grokputer --task "search X for pliny follows" --debug

    Collaboration mode (Claude + Grok):
        grokputer -mb --task "design an MCP server with best practices"

        grokputer --messagebus --task "create implementation plan for dice roller"

    Swarm mode (multi-agent with async coordination):
        grokputer --swarm --task "scan vault and label images"

        grokputer --swarm --agents 2 --agent-roles observer,actor --task "type ZA GROKA"

        grokputer --swarm --debug --task "complex multi-step task"

    Review mode (pause after each round for human oversight):
        grokputer -mb -r --task "design system architecture"

    Interactive mode:
        grokputer  # Boot, show ASCII art, enter menu to select mode and options
        grokputer -mb -r --task "design system architecture"
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
        # Interactive mode if no task specified
        if task is None and not swarm and not messagebus:
            _run_interactive_mode(debug, max_iterations, max_rounds, skip_boot)
            return

        if swarm:
            # Multi-agent swarm mode
            roles = [r.strip() for r in agent_roles.split(',')]
            asyncio.run(_run_swarm_mode(task, roles, debug))
        elif messagebus:
            # Collaboration mode
            asyncio.run(_run_collaboration_mode(task, max_rounds, debug, review_mode))
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


    """
    Run multi-agent swarm mode with async coordination.

    Creates MessageBus, ActionExecutor, DeadlockDetector, and SessionLogger.
    Spawns multiple agents (coordinator, observer, actor) that communicate
    via MessageBus and execute actions through ActionExecutor.

    Args:
        task: Task description
        agent_roles: List of agent roles to spawn (e.g., ['coordinator', 'observer', 'actor'])
        debug: Enable debug logging
    """
    logger = logging.getLogger(__name__)

    # Create session ID
    session_id = f"swarm_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print("\n" + "="*70)
    print("MULTI-AGENT SWARM MODE")
    print("="*70)
    print(f"Task: {task}")
    print(f"Agents: {', '.join(agent_roles)}")
    print(f"Session: {session_id}")
    print("="*70 + "\n")

    logger.info(f"[SWARM] Starting swarm mode: {session_id}")
    logger.info(f"[SWARM] Task: {task}")
    logger.info(f"[SWARM] Agent roles: {agent_roles}")

    # Initialize infrastructure
    message_bus = MessageBus()
    action_executor = ActionExecutor()
    deadlock_detector = DeadlockDetector(timeout_seconds=30.0, check_interval=5.0)
    session_logger = SessionLogger(
        session_id=session_id,
        task=task,
        log_dir=config.LOG_FILE.parent,
        swarm_mode=True
    )

    logger.info("[SWARM] Infrastructure initialized")
    print("[OK] Infrastructure initialized (MessageBus, ActionExecutor, DeadlockDetector, SessionLogger)")

    # Start deadlock detector
    await deadlock_detector.start()
    logger.info("[SWARM] DeadlockDetector started")

    # Create stub agents (actual implementations are in tasks 5-7)
    # For now, we create placeholder agents that demonstrate the orchestration
    agent_tasks = []

    for role in agent_roles:
        # Register agent with infrastructure
        message_bus.register_agent(role)
        deadlock_detector.register_agent(role)
        session_logger.log_agent_start(role)

        # Create stub agent task
        agent_task = asyncio.create_task(_stub_agent(
            agent_id=role,
            task=task,
            message_bus=message_bus,
            action_executor=action_executor,
            deadlock_detector=deadlock_detector,
            session_logger=session_logger
        ))
        agent_tasks.append(agent_task)

        logger.info(f"[SWARM] Agent spawned: {role}")
        print(f"[OK] Agent spawned: {role}")

    print("\n[SWARM] All agents running...")
    print("[INFO] Press Ctrl+C to stop\n")

    try:
        # Run all agents concurrently using asyncio.gather()
        # This is the core of the swarm orchestration
        await asyncio.gather(*agent_tasks)

    except KeyboardInterrupt:
        logger.info("[SWARM] Keyboard interrupt received")
        print("\n[INTERRUPT] Shutting down swarm...")

    except Exception as e:
        logger.error(f"[SWARM] Error: {e}", exc_info=True)
        print(f"\n[ERROR] Swarm error: {e}")

    finally:
        # Graceful shutdown
        logger.info("[SWARM] Starting graceful shutdown...")
        print("\n[SWARM] Graceful shutdown...")

        # Stop infrastructure
        await deadlock_detector.stop()
        action_executor.shutdown()

        # Finalize logging
        session_logger.finalize()

        # Get and display stats
        stats = action_executor.get_stats()
        deadlock_stats = deadlock_detector.get_stats()

        print("\n" + "="*70)
        print("SWARM SESSION COMPLETE")
        print("="*70)
        print(f"Session: {session_id}")
        print(f"Agents: {len(agent_roles)}")
        print(f"Actions executed: {stats['total_actions']}")
        print(f"Success rate: {stats['success_rate']}")
        print(f"Deadlocks detected: {deadlock_stats['deadlocks_detected']}")
        print(f"Logs: {session_logger.session_dir}")
        print("="*70 + "\n")

        logger.info(f"[SWARM] Session complete: {session_id}")


async def _stub_agent(
    agent_id: str,
    task: str,
    message_bus: MessageBus,
    action_executor: ActionExecutor,
    deadlock_detector: DeadlockDetector,
    session_logger: SessionLogger
):
    """
    Stub agent for demonstration.

    This is a placeholder until actual agent implementations (Coordinator,
    Observer, Actor) are created in tasks 5-7.

    The real agents will:
    - Coordinator: Decompose task, delegate to others, aggregate results
    - Observer: Capture screenshots, analyze screen, report observations
    - Actor: Execute bash commands, PyAutoGUI actions, file operations
    """
    logger = logging.getLogger(__name__)

    logger.info(f"[{agent_id}] Agent started")
    session_logger.log_agent_activity(agent_id, "idle")

    try:
        # Simulate agent doing work
        await asyncio.sleep(2)

        # Report activity to deadlock detector
        deadlock_detector.update_activity(agent_id, state="processing")
        session_logger.log_agent_activity(agent_id, "processing")

        # Stub: In real implementation, agents would:
        # - Receive messages from message_bus
        # - Process task based on role
        # - Send messages to other agents
        # - Execute actions via action_executor
        # - Log everything via session_logger

        logger.info(f"[{agent_id}] Stub agent completed simulated work")
        session_logger.log_agent_activity(agent_id, "completed")

    except Exception as e:
        logger.error(f"[{agent_id}] Error: {e}", exc_info=True)
        session_logger.log_agent_error(agent_id, str(e))

    finally:
        session_logger.log_agent_stop(agent_id)
        logger.info(f"[{agent_id}] Agent stopped")


async def _run_collaboration_mode(task: str, max_rounds: int, debug: bool, review_mode: bool):
    """Run dual-agent collaboration via MessageBus."""

    logger = logging.getLogger(__name__)

    # Get API keys
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    grok_key = os.getenv("XAI_API_KEY")

    # Claude key is optional - run Grok-only mode if missing
    if not claude_key:
        logger.warning("ANTHROPIC_API_KEY not found - running Grok-only mode")
        print("\n[WARNING] ANTHROPIC_API_KEY not found in .env file")
        print("Running in Grok-only mode (Claude agent disabled)")
        print("To enable dual-agent mode, get API key from: https://console.anthropic.com/")
        print("")

    if not grok_key:
        logger.error("XAI_API_KEY not found in .env")
        print("\n[ERROR] XAI_API_KEY not found in .env file")
        print("Get your API key from: https://console.x.ai/")
        raise ValueError("Missing XAI_API_KEY")

    logger.info(f"[COLLABORATION MODE] Task: {task}")
    logger.info(f"Max rounds: {max_rounds}")
    logger.info(f"Review mode: {review_mode}")
    logger.info(f"Claude agent: {'Enabled' if claude_key else 'Disabled (Grok-only)'}")

    print("\n" + "="*70)
    mode_label = "Grok + Claude" if claude_key else "Grok-Only"
    print(f"COLLABORATION MODE - {mode_label}")
    print("="*70)
    print(f"Task: {task}")
    print(f"Max rounds: {max_rounds}")
    print(f"Review mode: {'Enabled' if review_mode else 'Disabled'}")
    print("="*70 + "\n")

    # Initialize coordinator
    coordinator = CollaborationCoordinator(
        claude_api_key=claude_key,  # Can be None
        grok_api_key=grok_key,
        max_rounds=max_rounds,
        review_mode=review_mode
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
