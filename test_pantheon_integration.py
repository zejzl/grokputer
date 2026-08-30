#!/usr/bin/env python3
"""
Test Pantheon Integration with GG Framework

This script tests the Pantheon integration by invoking various Pantheon agents
through the GG workflow system.

Author: Grokputer Team
Date: 2026-01-11
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow.pantheon_integration import PantheonIntegration, PantheonNode
from src.workflow.flow import Workflow
from src.workflow.nodes.base import NodeContext


async def test_pantheon_integration():
    """Test basic Pantheon integration functionality."""

    print("=" * 70)
    print("TESTING PANTHEON INTEGRATION")
    print("=" * 70)

    # Initialize integration
    integration = PantheonIntegration()
    await integration.initialize()

    print("Pantheon integration initialized")
    print(f"   Available agents: {integration.list_agents()}")
    print()

    # Test each agent with mock responses
    test_agents = ["observer", "reasoner", "actor", "validator", "learner", "memory", "executor", "analyzer", "improver"]

    for agent_name in test_agents:
        print(f"Testing {agent_name} agent...")

        try:
            response = await integration.invoke_agent(
                agent_name=agent_name,
                task=f"Test task for {agent_name} agent",
                context={"test": True, "workflow_id": "test_workflow"}
            )

            print(f"   SUCCESS {agent_name}: {response.get('result', 'No result')[:50]}...")
            print(f"   Status: {response.get('status', 'unknown')}")

        except Exception as e:
            print(f"   FAILED {agent_name}: {e}")

        print()

    print("Pantheon integration test completed!")


async def test_pantheon_workflow_node():
    """Test Pantheon node in a workflow."""

    print("=" * 70)
    print("TESTING PANTHEON WORKFLOW NODE")
    print("=" * 70)

    # Create workflow with Pantheon node
    workflow = Workflow("pantheon_test")

    # Add Pantheon node
    pantheon_node = PantheonNode(
        "test_pantheon",
        name="Test Pantheon Agent",
        config={
            "agent": "observer",
            "task": "Observe the current system state and report findings",
            "context": {"test_mode": True}
        }
    )

    workflow.add_node(pantheon_node)

    # Execute workflow
    print("Executing workflow with Pantheon node...")

    try:
        result = await workflow.run({"test_input": "workflow_test"})

        print("Workflow completed successfully!")
        print(f"   Result: {result.get('pantheon_response', {}).get('result', 'No result')[:100]}...")
        print(f"   Agent: {result.get('agent', 'unknown')}")
        print(f"   Status: {result.get('status', 'unknown')}")

    except Exception as e:
        print(f"Workflow failed: {e}")
        import traceback
        traceback.print_exc()


async def test_multi_agent_workflow():
    """Test workflow with multiple Pantheon agents."""

    print("=" * 70)
    print("TESTING MULTI-AGENT PANTHEON WORKFLOW")
    print("=" * 70)

    workflow = Workflow("multi_agent_test")

    # Observer -> Reasoner -> Actor sequence
    observer_node = PantheonNode(
        "observe",
        name="Observe System",
        config={
            "agent": "observer",
            "task": "Observe the current system state and identify key metrics"
        }
    )

    reasoner_node = PantheonNode(
        "reason",
        name="Analyze Data",
        config={
            "agent": "reasoner",
            "task": "Analyze the observed data and determine optimal actions",
            "context": {"previous_agent": "observer"}
        }
    )

    actor_node = PantheonNode(
        "act",
        name="Execute Actions",
        config={
            "agent": "actor",
            "task": "Execute the recommended actions from the analysis"
        }
    )

    # Add nodes and connect
    workflow.add_node(observer_node)
    workflow.add_node(reasoner_node)
    workflow.add_node(actor_node)

    workflow.add_edge(observer_node, reasoner_node)
    workflow.add_edge(reasoner_node, actor_node)

    # Add hooks for monitoring
    workflow.on_start(lambda ctx: print("Multi-agent workflow started"))
    workflow.on_node_start(lambda node, ctx: print(f"Executing {node.name}"))
    workflow.on_node_complete(lambda node, ctx: print(f"Completed {node.name}"))
    workflow.on_complete(lambda ctx: print("Multi-agent workflow completed!"))

    print("Executing multi-agent workflow...")

    try:
        result = await workflow.run({"workflow_type": "multi_agent_test"})

        print("\nWORKFLOW RESULTS:")
        print(f"   Observer result: {result.get('observe', {}).get('pantheon_response', {}).get('result', 'N/A')[:50]}...")
        print(f"   Reasoner result: {result.get('reason', {}).get('pantheon_response', {}).get('result', 'N/A')[:50]}...")
        print(f"   Actor result: {result.get('act', {}).get('pantheon_response', {}).get('result', 'N/A')[:50]}...")

    except Exception as e:
        print(f"Multi-agent workflow failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all Pantheon tests."""

    print("Testing Pantheon Integration")
    print("Note: These tests use mock responses since Pantheon agents may not be running")
    print()

    try:
        await test_pantheon_integration()
        print()
        await test_pantheon_workflow_node()
        print()
        await test_multi_agent_workflow()

        print("\n" + "=" * 70)
        print("ALL PANTHEON TESTS COMPLETED!")
        print("=" * 70)
        print()
        print("Test Summary:")
        print("   - Basic integration test")
        print("   - Workflow node test")
        print("   - Multi-agent workflow test")
        print()
        print("Note: Tests use mock responses. For real Pantheon integration,")
        print("      ensure the main Grokputer system with Pantheon agents is running.")
        print()
        print("ZA GROKA. ZA PANTHEON. ZA GG.")

    except Exception as e:
        print(f"\nTests failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())