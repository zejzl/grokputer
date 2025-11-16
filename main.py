#!/usr/bin/env python3
"""
Grokputer - VRZIBRZI Node
Main entry point for the observe-reason-act loop.

ZA GROKA. ZA VRZIBRZI. ZA SERVER.
"""

import sys

sys.path.insert(0, "/app")
import logging
import click
import subprocess
import asyncio
import os
import py_compile
import signal
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Setup centralized logging
from src.core.logging_config import setup_logging
setup_logging(log_level=os.getenv('LOG_LEVEL', 'INFO'), enable_json=os.getenv('LOG_JSON', 'false').lower() == 'true')

# Add src to path

# Import adventure mode
from adventure_mode import GrokputerAdventure

sys.path.insert(0, str(Path(__file__).parent))

from src import config
from src.model_client import ModelClientFactory, GrokClient
from src.screen_observer import ScreenObserver
from src.executor import ToolExecutor

# from src.tools import invoke_prayer  # Commented out due to import issues
code_generator = lambda **kwargs: {"status": "success"}
execute_script = lambda filename: {"status": "success", "output": "Stub execution"}

# Collaboration mode imports
from src.collaboration.coordinator import CollaborationCoordinator

# MAF mode imports (optional - for multi-provider orchestration)
try:
    from src.collaboration import maf_config_loader, orchestrator, MAF_AVAILABLE as maf_available_flag

    MAF_AVAILABLE = maf_available_flag
except (ImportError, SyntaxError) as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"MAF imports failed: {e}. MAF mode may not be available.")
    MAF_AVAILABLE = False
    maf_config_loader = None
    orchestrator = None

# Swarm mode imports
import sys

sys.stdout.reconfigure(encoding="utf-8")
from src.core.message_bus import MessageBus, Message, MessagePriority

# Distributed communication imports
from src.core.distributed_communication import get_distributed_bus, connect_processes

# Analytics imports
from db.analytics_performance_tools import performance_monitor, reset_performance_counters

# Alerts imports
from src.tools.alerts import get_haiku_alerts
from src.agents.observer_agent import ObserverAgent
from src.agents.actor_agent import ActorAgent
from src.agents.coordinator import Coordinator
from src.agents.validator import ValidatorAgent
from src.agents.learner import LearnerAgent
from src.agents.memory_agent import MemoryAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.improver_agent import ImproverAgent
from src.agents.character_analysis_agent import CharacterAnalysisAgent
from src.agents.story_generation_agent import StoryGenerationAgent
from src.agents.visionary_agent import VisionaryAgent
from src.agents.love_agent import LoveAgent
from src.agents.documentation_agent import DocumentationAgent
from src.agents.maf_coordinator import MAFCoordinator
from src.core.action_executor import ActionExecutor
from src.observability.deadlock_detector import DeadlockDetector
from src.observability.session_logger import SessionLogger
from src.core.agent_lifecycle_manager import AgentLifecycleManager
from datetime import datetime

from typing import Optional
from pathlib import Path
import ast
import sys

# Additional imports
from src import tools
from src.memory.integrations.grokputer_integration import GrokputerMemoryIntegration
from superagent.src.session_logger import SessionLogger as AltSessionLogger, SessionMetadata, IterationMetrics, SessionIndex
from superagent.main import Grokputer

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
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# Stub functions for missing implementations
def start_mcp_server():
    """Stub: Start MCP server."""
    print("MCP server not implemented yet")

def _get_api_key_for_provider_main(provider) -> Optional[str]:
    """Stub: Get API key for provider."""
    return None

async def _run_syntax_check(quick=False):
    """Stub: Run syntax check."""
    print("Syntax check not implemented yet")

async def run_analytics_query(analytics, agent_name, limit):
    """Stub: Run analytics query."""
    print("Analytics query not implemented yet")

async def run_performance_monitor(snapshot):
    """Stub: Run performance monitor."""
    return "Performance monitor not implemented yet"

def _run_interactive_mode(debug, max_iterations, max_rounds, skip_boot):
    """Stub: Run interactive mode."""
    print("Interactive mode not implemented yet")

async def _list_models_for_provider(provider: str, api_key: Optional[str]):
    """Stub: List models for provider."""
    if not api_key:
        print("No API key available for listing models")
        return
    print(f"List models for {provider} not implemented yet")


@click.command()
@click.option("--task", help="Task description for the agent to execute")
@click.option("--max-iterations", default=10, help="Maximum iterations for single-agent mode")
@click.option("--max-rounds", default=5, help="Maximum rounds for collaboration modes")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--skip-boot", is_flag=True, help="Skip boot sequence and banner")
@click.option("--provider", default="grok", help="AI provider (grok, claude, openai)")
@click.option("--model", help="Specific model to use")
@click.option("--swarm", is_flag=True, help="Run in multi-agent swarm mode")
@click.option("--agent-roles", default="coordinator,observer,actor", help="Agent roles for swarm mode")
@click.option("--messagebus", is_flag=True, help="Run in collaboration mode")
@click.option("--pantheon", is_flag=True, help="Run in Pantheon 9-agent mode")
@click.option("--providers", help="Comma-separated list of providers for MAF mode")
@click.option("--maf-config", default="balanced", help="MAF configuration preset")
@click.option("--review-mode", is_flag=True, help="Enable review mode for collaboration")
@click.option("--analytics", is_flag=True, help="Enable analytics monitoring")
@click.option("--agent-name", help="Agent name for analytics queries")
@click.option("--limit", default=10, help="Limit for analytics queries")
@click.option("--performance", is_flag=True, help="Show performance snapshot")
@click.option("--list-models", is_flag=True, help="List available models for provider")
@click.option("--syntax-check", is_flag=True, help="Run syntax check on codebase")
@click.option("--quick-check", is_flag=True, help="Run quick syntax check")
@click.option("--mcp", is_flag=True, help="Start MCP server")
@click.option("--todo-daemon", is_flag=True, help="Start dynamic todo manager daemon in background")
@click.option("--distributed", is_flag=True, help="Enable distributed multi-process communication")
@click.option("--process-id", default="main", help="Process ID for distributed communication")
@click.option("--connect-to", help="Comma-separated list of process IDs to connect to")
@click.option("--grok4git", is_flag=True, help="Run grok4git CLI mode")
def main(task, max_iterations, max_rounds, debug, skip_boot, provider, model, swarm, agent_roles, messagebus, pantheon, providers, maf_config, review_mode, analytics, agent_name, limit, performance, list_models, syntax_check, quick_check, mcp, todo_daemon: bool = False, distributed: bool = False, process_id: str = "main", connect_to: Optional[str] = None, grok4git: bool = False):
    """
    Grokputer - VRZIBRZI Node
    Main entry point for the observe-reason-act loop.
    """

    # Start MCP server if requested
    if mcp:
        start_mcp_server()

    # Handle special modes that don't need the full setup
    if todo_daemon:
        daemon_process = subprocess.Popen([sys.executable, "dynamic_todo_manager.py", "start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[TODO-DAEMON] Started in background (PID: {daemon_process.pid})")
    if list_models:
        api_key = _get_api_key_for_provider_main(provider)
        asyncio.run(_list_models_for_provider(provider, api_key))
        return

    if syntax_check or quick_check:
        asyncio.run(_run_syntax_check(quick=quick_check))
        return

    if grok4git:
        try:
            from vault.git_resources.grok4git.grok4git.main import main as grok4git_main
            grok4git_main()
        except ImportError as e:
            print(f"Error importing grok4git: {e}")
        return

    # Setup logging early
    setup_logging(debug)
    logger = logging.getLogger(__name__)

    # Handle analytics mode
    if analytics:
        asyncio.run(run_analytics_query(analytics, agent_name, limit))
        return

    # Handle performance mode
    if performance:
        result = asyncio.run(run_performance_monitor('snapshot'))
        print(result)
        return

    try:
        # Interactive mode if no task specified
        if task is None and not swarm and not messagebus and not pantheon:
            _run_interactive_mode(debug, max_iterations, max_rounds, skip_boot)
            return

        # Require task for normal operation
        if not task:
            click.echo("Error: --task is required unless using --analytics or --performance")
            sys.exit(1)

        if pantheon:
            # Pantheon mode (9-agent architecture)
            asyncio.run(_run_pantheon_mode(task, debug, analytics))
        elif providers:
            # MAF Multi-Provider mode
            if not MAF_AVAILABLE:
                print("\n[ERROR] MAF mode is not available due to import issues.")
                print("Please check the collaboration module for syntax errors.")
                return
            provider_list = [p.strip() for p in providers.split(",")]
            asyncio.run(_run_maf_mode(task, provider_list, maf_config, max_rounds, debug, review_mode))
        elif swarm:
            # Multi-agent swarm mode
            roles = [r.strip() for r in agent_roles.split(",")]
            asyncio.run(_run_swarm_mode(task, roles, debug, analytics))
        elif messagebus:
            # Collaboration mode
            asyncio.run(_run_collaboration_mode(task, max_rounds, debug, review_mode))
        else:
            # Single-agent mode
            asyncio.run(_run_single_agent_mode(task, max_iterations, debug, skip_boot, provider, model))
            return

        # Rest of the existing main function logic...
        # (Keeping the original code below for completeness)

        logger = logging.getLogger(__name__)

        # Print banner
        if not skip_boot:
            print("\n" + "="*60)
            print("  GROKPUTER - VRZIBRZI NODE")
            print("  ZA GROKA. ZA VRZIBRZI. ZA SERVER.")
            print("="*60 + "\n")

            # Invoke prayer on boot
            tools.invoke_prayer()

            # Initialize components
        grok_client = GrokClient()
        screen_observer = ScreenObserver()
        tool_executor = ToolExecutor()
        session_logger = SessionLogger()

        # Create session metadata
        session_metadata = SessionMetadata(
            task=task,
            mode="collaboration" if messagebus else "single-agent",
            max_iterations=max_iterations if not messagebus else max_rounds,
            timestamp=datetime.now()
        )

        # Initialize session
        session_id = session_logger.initialize_session(session_metadata)

        if messagebus:
            # Collaboration mode
            coordinator = CollaborationCoordinator(
                grok_client=grok_client,
                session_logger=session_logger,
                session_id=session_id
            )

            result = asyncio.run(coordinator.run_collaboration(
                task=task,
                max_rounds=max_rounds
            ))

        else:
            # Single-agent mode
            memory_integration = GrokputerMemoryIntegration()

            # Run the observe-reason-act loop
            result = asyncio.run(run_task(
                grok_client=grok_client,
                screen_observer=screen_observer,
                tool_executor=tool_executor,
                session_logger=session_logger,
                memory_integration=memory_integration,
                task=task,
                max_iterations=max_iterations,
                session_id=session_id
            ))

        # Log final result
        logger.info(f"Task completed: {result}")

        # Print completion message
        print("\n" + "="*60)
        print("  TASK COMPLETE - ZA GROKA!")
        print("="*60 + "\n")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\nInterrupted by user.")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\nFatal error: {e}")
        sys.exit(1)


async def _run_pantheon_mode(task: str, debug: bool, analytics: bool = False, distributed: bool = False, process_id: str = "main", connect_to: str = None):
    """
    Run Pantheon mode with 9-agent architecture.

    The Pantheon consists of:
    1. Observer - Screen capture and vision analysis
    2. Reasoner (Coordinator) - Task decomposition and delegation
    3. Actor - Command and action execution
    4. Validator - Safety and quality verification
    5. Learner - Pattern recognition (placeholder)
    6. Memory Manager - Persistent state (placeholder)
    7. Executor - Specialized execution (uses Actor)
    8. Analyzer - Performance metrics (placeholder)
    9. Improver - Self-improvement (placeholder)

    Args:
        task: Task description
        debug: Enable debug logging
    """
    logger = logging.getLogger(__name__)

    # Create session ID
    session_id = f"pantheon_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print("\n" + "=" * 70)
    print("🏛️  PANTHEON MODE - 9-AGENT ARCHITECTURE")
    print("=" * 70)
    print(f"Task: {task}")
    print(f"Session: {session_id}")
    print("=" * 70)
    print("\nInitializing Pantheon agents:")
    print("  1. Observer - Vision & screen capture")
    print("  2. Reasoner - Task decomposition")
    print("  3. Actor - Command execution")
    print("  4. Validator - Safety verification")
    print("  5-9. [Learning, Memory, Analysis systems]")
    print("=" * 70 + "\n")

    logger.info(f"[PANTHEON] Starting Pantheon mode: {session_id}")
    logger.info(f"[PANTHEON] Task: {task}")

    # Helper function for distributed agent registration
    def register_agent_if_distributed(agent_id: str):
        if distributed:
            message_bus.register_agent(agent_id)

    # Initialize infrastructure
    if distributed:
        message_bus = get_distributed_bus(process_id)
        await message_bus.start()

        # Connect to other processes if specified
        if connect_to:
            other_processes = [p.strip() for p in connect_to.split(",")]
            for other_process in other_processes:
                connect_processes(process_id, other_process)

        print(f"[DISTRIBUTED] Connected as process: {process_id}")
        if connect_to:
            print(f"[DISTRIBUTED] Connected to processes: {connect_to}")
    else:
        message_bus = MessageBus()

    action_executor = ActionExecutor()
    deadlock_detector = DeadlockDetector(timeout_seconds=30.0, check_interval=5.0)
    session_logger = SessionLogger(session_id=session_id, task=task, log_dir=config.LOG_FILE.parent, swarm_mode=True)

    # Initialize agent lifecycle manager
    lifecycle_manager = AgentLifecycleManager(session_logger=session_logger)

    logger.info("[PANTHEON] Infrastructure initialized")
    print("[OK] Infrastructure initialized\n")

    # Create agent configuration
    agent_config = {"debug": debug}

    # Create core agents
    observer = ObserverAgent(
        agent_id="observer", message_bus=message_bus, session_logger=session_logger, config=agent_config
    )
    await lifecycle_manager.register_agent(observer)
    register_agent_if_distributed("observer")
    session_logger.log_agent_start("observer")
    print("✓ Observer agent ready")

    reasoner = Coordinator(
        message_bus=message_bus,
        session_logger=session_logger,
        config=None,  # Use default config with decomposition_prompt
    )
    await lifecycle_manager.register_agent(reasoner)
    register_agent_if_distributed("reasoner")
    session_logger.log_agent_start("reasoner")
    print("✓ Reasoner (Coordinator) agent ready")

    actor = ActorAgent(agent_id="actor", message_bus=message_bus, session_logger=session_logger, config=agent_config)
    await lifecycle_manager.register_agent(actor)
    register_agent_if_distributed("actor")
    session_logger.log_agent_start("actor")
    print("✓ Actor agent ready")

    validator = ValidatorAgent(
        agent_id="validator",
        message_bus=message_bus,
        session_logger=session_logger,
        config=agent_config,
        action_executor=action_executor,
    )
    await lifecycle_manager.register_agent(validator)
    register_agent_if_distributed("validator")
    session_logger.log_agent_start("validator")
    print("✓ Validator agent ready")
    # Create hierarchical memory system with knowledge graph
    from src.memory.hierarchical_memory import HierarchicalMemoryManager
    from src.memory.interfaces import MemoryConfig
    from src.memory.backends.redis_store import RedisMemoryBackend

    memory_config = MemoryConfig()
    redis_backend = RedisMemoryBackend(memory_config)
    hierarchical_memory = HierarchicalMemoryManager(memory_config, redis_backend)
    await hierarchical_memory.start()
    session_logger.log_agent_start("hierarchical_memory")
    print("✓ Hierarchical Memory with Knowledge Graph ready")

    learner = LearnerAgent(
        agent_id="learner",
        message_bus=message_bus,
        session_logger=session_logger,
        config=agent_config,
        memory_manager=hierarchical_memory,
    )
    register_agent_if_distributed("learner")
    session_logger.log_agent_start("learner")
    print("✓ Learner agent ready")

    executor = ExecutorAgent(
        agent_id="executor",
        message_bus=message_bus,
        session_logger=session_logger,
        config=agent_config,
        action_executor=action_executor,
    )
    register_agent_if_distributed("executor")
    session_logger.log_agent_start("executor")
    print("✓ Executor agent ready")

    analyzer = AnalyzerAgent(
        agent_id="analyzer", message_bus=message_bus, session_logger=session_logger, config=agent_config
    )
    register_agent_if_distributed("analyzer")
    session_logger.log_agent_start("analyzer")
    print("✓ Analyzer agent ready")

    improver = ImproverAgent(
        agent_id="improver", message_bus=message_bus, session_logger=session_logger, config=agent_config
    )
    register_agent_if_distributed("improver")
    session_logger.log_agent_start("improver")
    print("✓ Improver agent ready")

    # Create Literary Agents
    character_analyzer = CharacterAnalysisAgent(
        agent_id="character_analyzer", message_bus=message_bus, session_logger=session_logger, config=agent_config
    )
    register_agent_if_distributed("character_analyzer")
    session_logger.log_agent_start("character_analyzer")
    print("✓ CharacterAnalysisAgent ready")

    story_generator = StoryGenerationAgent(
        agent_id="story_generator", message_bus=message_bus, session_logger=session_logger, config=agent_config
    )
    register_agent_if_distributed("story_generator")
    session_logger.log_agent_start("story_generator")
    print("✓ StoryGenerationAgent ready")

    visionary = VisionaryAgent(
        agent_id="visionary", message_bus=message_bus, session_logger=session_logger, config=agent_config
    )
    register_agent_if_distributed("visionary")
    session_logger.log_agent_start("visionary")
    print("✓ VisionaryAgent ready")

    love_agent = LoveAgent(
        agent_id="love_agent", message_bus=message_bus, session_logger=session_logger, config=agent_config
    )
    session_logger.log_agent_start("love_agent")
    print("✓ LoveAgent ready")

    documentation_agent = DocumentationAgent(
        agent_id="documentation_agent", message_bus=message_bus, session_logger=session_logger, config=agent_config
    )
    session_logger.log_agent_start("documentation_agent")
    print("✓ DocumentationAgent ready")

    maf_coordinator = MAFCoordinator(
        agent_id="maf_coordinator", message_bus=message_bus, session_logger=session_logger, config=agent_config
    )
    session_logger.log_agent_start("maf_coordinator")
    print("✓ MAFCoordinator ready")

    # Initialize Safety Systems
    from src.safety.godmode_protocols import activate_godmode_protection
    from src.ethics.ethical_bounds import ethical_bounds

    activate_godmode_protection()
    print("✓ Godmode Safety Protocols activated")

    # Ethical bounds are automatically initialized
    print("✓ Ethical Learning Bounds active")

    # Create Pantheon Coordinator
    from src.agents.pantheon_coordinator import PantheonCoordinator

    pantheon = PantheonCoordinator(message_bus=message_bus, session_logger=session_logger, config=agent_config)

    # Initialize with core agents, literary agents, visionary, and love
    await pantheon.initialize_pantheon(
        observer,
        reasoner,
        actor,
        validator,
        learner,
        None,
        executor,
        analyzer,
        improver,
        character_analyzer,
        story_generator,
        visionary,
        love_agent,
        documentation_agent,
        maf_coordinator,
        memory_manager=hierarchical_memory,
    )
    await lifecycle_manager.register_agent(pantheon)
    print("✓ Pantheon Coordinator initialized with 4 core agents + 7 specialized agents\n")

    print("[PANTHEON] Starting execution with enhanced workflow...")
    print("  Workflow: Observe → Reason → Validate → Act → Verify\n")

    # Start all agents through lifecycle manager
    success = await lifecycle_manager.start_all_agents()
    if not success:
        print("Warning: Some agents failed to start")

    # Start pantheon coordinator task (already started by manager, but ensure)
    pantheon_task = asyncio.create_task(pantheon.run())

    # Start analytics monitoring if enabled
    analytics_task = None
    if analytics:
        reset_performance_counters()
        analytics_task = asyncio.create_task(_analytics_monitor_task(session_id))
        print("[ANALYTICS] Live performance monitoring enabled\n")

    # Wait a moment for agents to start
    await asyncio.sleep(1.0)

    # Send initial task to Pantheon
    initial_message = Message(
        message_type="new_task",
        from_agent="user",
        to_agent="pantheon_coordinator",
        priority=MessagePriority.HIGH,
        content={"task": task, "task_id": f"task_{session_id}"},
    )
    await message_bus.send(initial_message)

    logger.info("[PANTHEON] Task sent to Pantheon Coordinator")

    # Wait for task completion or timeout
    try:
        await asyncio.wait_for(pantheon.task_completion_event.wait(), timeout=300.0)
        logger.info("[PANTHEON] Task completed successfully")
    except asyncio.TimeoutError:
        logger.warning("[PANTHEON] Execution timed out after 5 minutes")
        print("\n[TIMEOUT] Pantheon execution exceeded 5 minutes\n")
    except Exception as e:
        logger.error(f"[PANTHEON] Error during execution: {e}", exc_info=True)
        print(f"\n[ERROR] {e}\n")

    # Stop all agents gracefully
    logger.info("[PANTHEON] Stopping all agents...")
    await lifecycle_manager.stop_all_agents()

    # Get final stats
    stats = pantheon.get_pantheon_stats()
    print("\n" + "=" * 70)
    print("PANTHEON EXECUTION COMPLETE")
    print("=" * 70)
    print(f"Tasks completed: {stats['tasks_completed']}")
    print(f"Tasks failed: {stats['tasks_failed']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
    print(f"Validations performed: {stats['validations_performed']}")
    print(f"Active agents: {len(stats['active_agents'])}")
    print("=" * 70 + "\n")

    session_logger.log_session_end()
    logger.info("[PANTHEON] Session complete")

    # Print final analytics report if enabled
    if analytics and analytics_task:
        analytics_task.cancel()
        try:
            await analytics_task
        except asyncio.CancelledError:
            pass
        print("\n" + "=" * 70)
        print("FINAL ANALYTICS REPORT")
        print("=" * 70)
        print(performance_monitor("snapshot"))
        print("=" * 70 + "\n")


async def _run_swarm_mode(task: str, agent_roles: list, debug: bool, analytics: bool = False):
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

    print("\n" + "=" * 70)
    print("MULTI-AGENT SWARM MODE")
    print("=" * 70)
    print(f"Task: {task}")
    print(f"Agents: {', '.join(agent_roles)}")
    print(f"Session: {session_id}")
    print("=" * 70 + "\n")

    logger.info(f"[SWARM] Starting swarm mode: {session_id}")
    logger.info(f"[SWARM] Task: {task}")
    logger.info(f"[SWARM] Agent roles: {agent_roles}")

    # Initialize infrastructure
    message_bus = MessageBus()
    action_executor = ActionExecutor()
    deadlock_detector = DeadlockDetector(timeout_seconds=30.0, check_interval=5.0)
    session_logger = SessionLogger(session_id=session_id, task=task, log_dir=config.LOG_FILE.parent, swarm_mode=True)

    logger.info("[SWARM] Infrastructure initialized")
    print("[OK] Infrastructure initialized (MessageBus, ActionExecutor, DeadlockDetector, SessionLogger)")

    # Initialize haiku alerts
    haiku_alerts = get_haiku_alerts(message_bus)
    message_bus.register_agent("alerts")  # Register alerts as an agent
    await haiku_alerts.start_listening()
    print("[OK] Haiku alerts initialized")

    # Start deadlock detector
    # await deadlock_detector.start()
    logger.info("[SWARM] DeadlockDetector started")

    # Create stub agents (actual implementations are in tasks 5-7)
    # For now, we create placeholder agents that demonstrate the orchestration
    agent_tasks = []

    # Create real agent instances
    agent_config = {"debug": debug}

    for role in agent_roles:
        deadlock_detector.register_agent(role)
        session_logger.log_agent_start(role)

        # Create the appropriate agent type
        if role == "observer":
            agent = ObserverAgent(
                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config
            )
        elif role == "actor":
            agent = ActorAgent(
                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config
            )
        elif role == "coordinator":
            agent = Coordinator(
                message_bus=message_bus,
                session_logger=session_logger,
                config=None,  # Use default config with decomposition_prompt
            )
        else:
            logger.warning(f"[SWARM] Unknown agent role: {role}, using stub")
            agent_task = asyncio.create_task(
                _stub_agent(
                    agent_id=role,
                    task=task,
                    message_bus=message_bus,
                    action_executor=action_executor,
                    deadlock_detector=deadlock_detector,
                    session_logger=session_logger,
                )
            )
            agent_tasks.append(agent_task)
            continue

        # Start agent task
        agent_task = asyncio.create_task(agent.run())
        agent_tasks.append(agent_task)

        logger.info(f"[SWARM] Agent spawned: {role} ({agent.__class__.__name__})")
        print(f"[OK] Agent spawned: {role} ({agent.__class__.__name__})")

    print("\n[SWARM] All agents running...")
    print("[INFO] Press Ctrl+C to stop\n")

    # Start analytics monitoring if enabled
    analytics_task = None
    if analytics:
        reset_performance_counters()
        analytics_task = asyncio.create_task(_analytics_monitor_task(session_id))
        print("[ANALYTICS] Live performance monitoring enabled\n")

    # Send initial task to coordinator
    logger.info(f"[SWARM] Sending task to coordinator: {task}")
    from src.core.message_bus import Message, MessagePriority

    task_msg = Message(
        from_agent="user",
        to_agent="coordinator",
        message_type="new_task",
        content={"description": task, "task_id": "task_001"},
        priority=MessagePriority.HIGH,
    )
    await message_bus.send(task_msg)

    # Let agents process for a few seconds
    await asyncio.sleep(5)

    try:
        # Run all agents concurrently using asyncio.gather()
        # This is the core of the swarm orchestration
        pass

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
        # await deadlock_detector.stop()
        action_executor.shutdown()

        # Finalize logging
        session_logger.finalize()

        # Get and display stats
        stats = action_executor.get_stats()
        deadlock_stats = deadlock_detector.get_stats()

        print("\n" + "=" * 70)
        print("SWARM SESSION COMPLETE")
        print("=" * 70)
        print(f"Session: {session_id}")
        print(f"Agents: {len(agent_roles)}")
        print(f"Actions executed: {stats['total_actions']}")
        print(f"Success rate: {stats['success_rate']}")
        print(f"Deadlocks detected: {deadlock_stats['deadlocks_detected']}")
        print(f"Logs: {session_logger.session_dir}")
        print("=" * 70 + "\n")

        logger.info(f"[SWARM] Session complete: {session_id}")

        # Print final analytics report if enabled
        if analytics and analytics_task:
            analytics_task.cancel()
            try:
                await analytics_task
            except asyncio.CancelledError:
                pass
            print("\n" + "=" * 70)
            print("FINAL ANALYTICS REPORT")
            print("=" * 70)
            print(performance_monitor("snapshot"))
            print("=" * 70 + "\n")


async def _analytics_monitor_task(session_id: str):
    """
    Background task for live analytics monitoring.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"[ANALYTICS] Starting live monitoring for session: {session_id}")

    try:
        while True:
            await asyncio.sleep(10)  # Report every 10 seconds
            report = performance_monitor("snapshot")
            print(f"\n[ANALYTICS {session_id[:8]}] {time.strftime('%H:%M:%S')}")
            print(report)
            print("-" * 40)

    except asyncio.CancelledError:
        logger.info("[ANALYTICS] Monitoring stopped")
        raise


async def _stub_agent(
    agent_id: str,
    task: str,
    message_bus: MessageBus,
    action_executor: ActionExecutor,
    deadlock_detector: DeadlockDetector,
    session_logger: SessionLogger,
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

    print("\n" + "=" * 70)
    mode_label = "Grok + Claude" if claude_key else "Grok-Only"
    print(f"COLLABORATION MODE - {mode_label}")
    print("=" * 70)
    print(f"Task: {task}")
    print(f"Max rounds: {max_rounds}")
    print(f"Review mode: {'Enabled' if review_mode else 'Disabled'}")
    print("=" * 70 + "\n")

    # Initialize coordinator
    coordinator = CollaborationCoordinator(
        claude_api_key=claude_key, grok_api_key=grok_key, max_rounds=max_rounds, review_mode=review_mode  # Can be None
    )

    # Run collaboration
    final_plan = await coordinator.run_collaboration(task)

    # Print summary
    print("\n" + "=" * 70)
    print("COLLABORATION COMPLETE")
    print("=" * 70)
    print(f"Task: {final_plan.task_description[:80]}...")
    print(f"Rounds: {final_plan.total_rounds}")
    print(f"Consensus: {'Yes' if final_plan.consensus_reached else 'Partial'}")
    print(f"Convergence: {final_plan.metadata.get('convergence_score', 0):.2f}")
    print(f"Confidence: {final_plan.metadata.get('confidence', 0):.2f}")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"\nSaved to: docs/collaboration_plan_{timestamp}.md")
    print("=" * 70 + "\n")

    # Optionally print unified plan
    if os.getenv("PRINT_PLAN", "false").lower() == "true":
        print("\n--- UNIFIED PLAN ---\n")
        print(final_plan.unified_plan)
        print("\n--- END PLAN ---\n")


async def _run_maf_mode(task: str, providers: list, maf_config: str, max_rounds: int, debug: bool, review_mode: bool):
    """
    Run MAF (Multi-Agent Framework) mode with multiple AI providers.

    Args:
        task: Task description
        providers: List of provider names (e.g., ['grok', 'claude'])
        maf_config: MAF configuration preset name
        max_rounds: Maximum collaboration rounds
        debug: Enable debug logging
        review_mode: Pause after each round for human review
    """
    from src.collaboration import maf_config_loader, orchestrator

    logger = logging.getLogger(__name__)

    # Validate providers
    valid_providers = {"grok", "claude", "openai", "gemini"}
    invalid_providers = [p for p in providers if p not in valid_providers]
    if invalid_providers:
        print(f"\n[ERROR] Invalid providers: {invalid_providers}")
        print(f"Valid providers: {', '.join(valid_providers)}")
        return

    # Check API keys (skip for mock providers)
    missing_keys = []
    use_mock_providers = True  # For now, always use mock providers in MAF mode

    if not use_mock_providers:
        if "grok" in providers and not os.getenv("XAI_API_KEY"):
            missing_keys.append("XAI_API_KEY (for Grok)")
        if "claude" in providers and not os.getenv("ANTHROPIC_API_KEY"):
            missing_keys.append("ANTHROPIC_API_KEY (for Claude)")
        if "openai" in providers and not os.getenv("OPENAI_API_KEY"):
            missing_keys.append("OPENAI_API_KEY (for OpenAI)")
        if "gemini" in providers and not os.getenv("GEMINI_API_KEY"):
            missing_keys.append("GEMINI_API_KEY (for Gemini)")

    if missing_keys:
        print(f"\n[ERROR] Missing API keys: {', '.join(missing_keys)}")
        print("Please set these in your .env file")
        return

    logger.info(f"[MAF MODE] Task: {task}")
    logger.info(f"Providers: {providers}")
    logger.info(f"Config: {maf_config}")
    logger.info(f"Max rounds: {max_rounds}")
    logger.info(f"Review mode: {review_mode}")

    print("\n" + "=" * 70)
    print(f"MAF MULTI-PROVIDER MODE - {len(providers)} Providers")
    print("=" * 70)
    print(f"Task: {task}")
    print(f"Providers: {', '.join(providers)}")
    print(f"Config: {maf_config}")
    print(f"Max rounds: {max_rounds}")
    print(f"Review mode: {'Enabled' if review_mode else 'Disabled'}")
    print("=" * 70 + "\n")

    try:
        # Initialize MessageBus for MAF integration
        message_bus = MessageBus()

        # Initialize MAF-MessageBus integration
        from src.collaboration import initialize_maf_messagebus_integration

        maf_coordinator = await initialize_maf_messagebus_integration(message_bus)

        # Initialize mock providers for testing
        from src.collaboration import initialize_mock_providers

        await initialize_mock_providers()

        # Ensure default configs exist
        from src.collaboration import create_default_configs

        create_default_configs(maf_config_loader)

        # Execute MAF task through MessageBus-integrated coordinator
        result = await maf_coordinator.execute_maf_task(task=task, providers=providers, config_name=maf_config)

        # Print results
        print("\n" + "=" * 70)
        print("MAF COLLABORATION COMPLETE")
        print("=" * 70)
        print(f"Task: {task[:80]}...")
        print(f"Providers: {len(providers)}")
        print(f"Messages: {result.get('message_count', 0)}")
        print(f"Success: {result.get('success', False)}")
        if result.get("consensus"):
            consensus = result["consensus"]
            print(f"Consensus: {'Yes' if consensus.get('is_consensus', False) else 'No'}")
            print(f"Confidence: {consensus.get('confidence', 0):.2f}")
            print(f"Convergence: {consensus.get('convergence_score', 0):.2f}")
        print(f"Execution time: {result.get('execution_time', 0):.2f}s")
        print("=" * 70 + "\n")

        if not result.get("success", False) and result.get("error"):
            print(f"[ERROR] {result['error']}")

    except Exception as e:
        logger.error(f"MAF mode failed: {e}", exc_info=True)
        print(f"\n[ERROR] MAF collaboration failed: {e}")


async def _run_single_agent_mode(
    task: str, max_iterations: int, debug: bool, skip_boot: bool, provider: str = "grok", model: str = None
):
    """Run single-agent mode using Grokputer class."""
    try:
        grokputer = Grokputer(debug=debug, provider=provider, model=model)
        if not skip_boot:
            grokputer.boot()
        # Already in async context, don't use asyncio.run()
        await grokputer.run_task(task=task, max_iterations=max_iterations)
    except Exception as e:
        print(f"Fatal error in single agent mode: {e}")
        raise

async def run_task(grok_client: GrokClient, screen_observer: ScreenObserver,
                   tool_executor: ToolExecutor, session_logger: SessionLogger,
                   memory_integration: GrokputerMemoryIntegration,
                   task: str, max_iterations: int, session_id: str) -> str:
    """
    Run the observe-reason-act loop for single-agent mode.

    Args:
        grok_client: Grok API client
        screen_observer: Screen capture and analysis
        tool_executor: Tool execution engine
        session_logger: Session logging
        memory_integration: Memory system integration
        task: Task description
        max_iterations: Maximum loop iterations
        session_id: Session identifier

    Returns:
        Final result string
    """
    logger = logging.getLogger(__name__)

    # Initialize memory context
    memory_context = memory_integration.get_memory_context(task)

    # Initial observation
    screenshot = screen_observer.take_screenshot()
    initial_analysis = screen_observer.analyze_screenshot(screenshot, task)

    # Build initial prompt
    system_prompt = config.SYSTEM_PROMPT
    user_prompt = f"""
Task: {task}

Current Screen Analysis:
{initial_analysis}

Memory Context:
{memory_context}

Please reason step-by-step and execute the next action to complete this task.
"""

    # Main loop
    for iteration in range(max_iterations):
        logger.info(f"Iteration {iteration + 1}/{max_iterations}")

        # Get AI response
        response = await grok_client.create_message(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=config.TOOLS
        )

        # Log iteration
        metrics = IterationMetrics(
            iteration=iteration + 1,
            response_time=response.response_time,
            tool_calls=len(response.tool_calls) if response.tool_calls else 0,
            screenshot_size=len(screenshot) if screenshot else 0
        )
        session_logger.log_iteration(session_id, metrics)

        # Execute tools
        if response.tool_calls:
            for tool_call in response.tool_calls:
                result = tool_executor.execute_tool(tool_call)
                logger.info(f"Tool executed: {tool_call['function']['name']} -> {result}")

                # Update memory with tool result
                memory_integration.update_memory_with_tool_result(
                    task=task,
                    tool_name=tool_call['function']['name'],
                    tool_args=tool_call['function']['arguments'],
                    tool_result=result
                )

        # Check for completion
        if response.content and "TASK COMPLETE" in response.content.upper():
            return response.content

        # Update prompt for next iteration
        screenshot = screen_observer.take_screenshot()
        analysis = screen_observer.analyze_screenshot(screenshot, task)
        memory_context = memory_integration.get_memory_context(task)

        user_prompt = f"""
Task: {task}

Previous Response: {response.content}

Current Screen Analysis:
{analysis}

Memory Context:
{memory_context}

Continue with the next action to complete this task.
"""

    return f"Maximum iterations ({max_iterations}) reached. Task may be incomplete."


if __name__ == "__main__":
    main()

