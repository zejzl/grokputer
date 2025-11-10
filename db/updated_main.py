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
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import config
from src.grok_client import GrokClient
from src.screen_observer import ScreenObserver
from src.executor import ToolExecutor
from src.tools import invoke_prayer, analytics_query_tool, performance_monitor_tool
from src.memory.integrations.grokputer_integration import GrokputerMemoryIntegration
from src.session_logger import SessionLogger, SessionMetadata, IterationMetrics, SessionIndex

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
            logging.StreamHandler()
        ]
    )


async def run_analytics_query(query_type: str, agent_name: str = None, limit: int = 10):
    """Run analytics query and return formatted results."""
    params = {
        'query_type': query_type,
        'limit': limit
    }
    if agent_name:
        params['agent_name'] = agent_name

    result = await analytics_query_tool(params)

    if result['status'] == 'success':
        if query_type == 'summary':
            data = result['data']
            return f"""
Swarm Rolls Summary:
- Total Rolls: {data['total_rolls']}
- Unique Agents: {data['agents']}
- Average Total: {data['avg_total']:.2f}
- Max Total: {data['max_total']}
"""

        elif query_type == 'top_agents':
            data = result['data']
            output = "Top Agents by Average Total:\n"
            for item in data:
                output += f"- {item['agent']}: Rolls={item['rolls']}, Avg={item['avg_total']:.2f}, Max={item['max_total']}\n"
            return output

        elif query_type == 'agent_stats':
            data = result['data']
            return f"""
Stats for {data['agent']}:
- Rolls: {data['rolls']}
- Avg Total: {data['avg_total']:.2f}
- Min Total: {data['min_total']}
- Max Total: {data['max_total']}
"""

        elif query_type == 'roll_distribution':
            data = result['data']
            output = "Roll Total Distribution:\n"
            for item in data:
                output += f"- {item['total']}: {item['count']} rolls\n"
            return output
    else:
        return f"Error: {result.get('error', 'Unknown error')}"


async def run_performance_monitor(mode: str = 'snapshot'):
    """Run performance monitor and return formatted results."""
    result = await performance_monitor_tool({'mode': mode})

    if result['status'] == 'success':
        if mode == 'reset':
            return result.get('message', 'Counters reset')

        data = result['data']
        system = data['system']
        api = data['api']

        return f"""
Performance Snapshot (Uptime: {data['uptime_seconds']:.1f}s):

System Metrics:
- CPU Usage: {system['cpu_percent']:.1f}%
- Memory: {system['memory_percent']:.1f}% used ({system['memory_used_gb']:.1f}GB / {system['memory_total_gb']:.1f}GB)
- Disk: {system['disk_percent']:.1f}% used ({system['disk_used_gb']:.1f}GB / {system['disk_total_gb']:.1f}GB)

API Metrics:
- Total Calls: {api['total_calls']}
- Avg Response Time: {api['avg_response_time']:.2f}s
- Calls per Agent: {api['calls_per_agent']}
"""
    else:
        return f"Error: {result.get('error', 'Unknown error')}"


@click.command()
@click.option('--task', '-t', help='Task description for Grokputer to execute')
@click.option('--max-iterations', '-m', default=10, help='Maximum loop iterations (single-agent mode)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--skip-boot', is_flag=True, help='Skip boot sequence')
@click.option('--messagebus', '-mb', is_flag=True, help='Enable collaboration mode (Claude + Grok)')
@click.option('--max-rounds', default=5, help='Maximum collaboration rounds (messagebus mode only)')
@click.option('--analytics', help='Run analytics query (summary, top_agents, agent_stats, roll_distribution)')
@click.option('--performance', is_flag=True, help='Show performance metrics')
@click.option('--agent-name', help='Agent name for agent_stats query')
@click.option('--limit', default=10, help='Limit for analytics results')
def main(task: str, max_iterations: int, debug: bool, skip_boot: bool, messagebus: bool, max_rounds: int,
         analytics: str, performance: bool, agent_name: str, limit: int):
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

    Analytics mode:
        grokputer --analytics summary

        grokputer --analytics top_agents --limit 5

        grokputer --analytics agent_stats --agent-name Alice

    Performance mode:
        grokputer --performance
    """
    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logging(debug)

    # Handle analytics mode
    if analytics:
        asyncio.run(run_analytics_query(analytics, agent_name, limit))
        return

    # Handle performance mode
    if performance:
        result = asyncio.run(run_performance_monitor('snapshot'))
        print(result)
        return

    # Require task for normal operation
    if not task:
        click.echo("Error: --task is required unless using --analytics or --performance")
        sys.exit(1)

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
        invoke_prayer()

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

    try:
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