#!/usr/bin/env python3
"""
GG Framework Quickstart Example

This demonstrates the basic workflow capabilities:
- Creating nodes
- Connecting them into a workflow
- Executing asynchronously

Author: Grokputer Team
Date: 2025-11-14
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow.flow import Workflow
from src.workflow.nodes.base import BaseNode, NodeContext
from src.workflow.nodes.transform import TransformNode


# Define custom nodes for this example
class GreetingNode(BaseNode):
    """Node that creates a greeting."""

    async def execute(self, context: NodeContext) -> NodeContext:
        name = context.get("name", "World")
        greeting = f"Hello, {name}!"
        context.set("greeting", greeting)
        print(f"[GreetingNode] {greeting}")
        return context


class UppercaseNode(TransformNode):
    """Transform text to uppercase."""

    def __init__(self, node_id: str):
        super().__init__(
            node_id,
            transform_func=lambda data: {
                **data,
                "greeting": data.get("greeting", "").upper(),
            },
        )


class AddExclamationNode(BaseNode):
    """Add extra excitement."""

    async def execute(self, context: NodeContext) -> NodeContext:
        greeting = context.get("greeting", "")
        context.set("greeting", greeting + "!!!")
        print(f"[AddExclamationNode] {context.get('greeting')}")
        return context


async def example_1_simple_chain():
    """Example 1: Simple linear workflow."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Simple Chain")
    print("=" * 70)

    # Create workflow
    workflow = Workflow("simple_chain")

    # Create nodes
    greet = GreetingNode("greet")
    uppercase = UppercaseNode("uppercase")
    exclaim = AddExclamationNode("exclaim")

    # Add nodes and connect them
    workflow.add_node(greet).add_node(uppercase).add_node(exclaim)

    workflow.add_edge(greet, uppercase).add_edge(uppercase, exclaim)

    # Execute
    result = await workflow.run({"name": "Grokputer"})

    print(f"\nFinal result: {result['greeting']}")


async def example_2_parallel():
    """Example 2: Parallel execution."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Parallel Execution")
    print("=" * 70)

    workflow = Workflow("parallel")

    # Create multiple greetings in parallel
    greet1 = GreetingNode("greet1")
    greet2 = GreetingNode("greet2")

    # Transform nodes (will run in parallel)
    upper1 = TransformNode(
        "upper1",
        transform_func=lambda d: {**d, "greeting": d.get("greeting", "").upper()},
    )
    upper2 = TransformNode(
        "upper2",
        transform_func=lambda d: {**d, "greeting": d.get("greeting", "").lower()},
    )

    # Add nodes
    for node in [greet1, greet2, upper1, upper2]:
        workflow.add_node(node)

    # Connect in parallel branches
    workflow.add_edge(greet1, upper1)
    workflow.add_edge(greet2, upper2)

    # Execute
    result = await workflow.run({"name": "Parallel"})

    print(f"\nFinal result: {result}")


async def example_3_transform():
    """Example 3: Data transformation."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Data Transformation")
    print("=" * 70)

    workflow = Workflow("transform")

    # Create transform nodes
    double = TransformNode(
        "double",
        transform_func=lambda d: {**d, "value": d.get("value", 0) * 2},
    )

    add_ten = TransformNode(
        "add_ten",
        transform_func=lambda d: {**d, "value": d.get("value", 0) + 10},
    )

    square = TransformNode(
        "square",
        transform_func=lambda d: {**d, "value": d.get("value", 0) ** 2},
    )

    # Chain transformations
    workflow.add_node(double).add_node(add_ten).add_node(square)
    workflow.add_edge(double, add_ten).add_edge(add_ten, square)

    # Execute
    result = await workflow.run({"value": 5})

    print(f"\nTransformation chain: 5 -> *2 -> +10 -> ^2")
    print(f"Result: {result['value']}")  # (5*2 + 10)^2 = 400


async def example_4_with_hooks():
    """Example 4: Using hooks for monitoring."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Workflow Hooks")
    print("=" * 70)

    workflow = Workflow("with_hooks")

    # Add hooks
    workflow.on_start(lambda ctx: print("[HOOK] Workflow started"))
    workflow.on_complete(lambda ctx: print("[HOOK] Workflow completed"))
    workflow.on_node_start(lambda node, ctx: print(f"[HOOK] Node {node.node_id} starting"))
    workflow.on_node_complete(lambda node, ctx: print(f"[HOOK] Node {node.node_id} completed"))

    # Simple workflow
    greet = GreetingNode("greet")
    workflow.add_node(greet)

    # Execute
    await workflow.run({"name": "Hooks"})


async def main():
    """Run all examples."""
    print()
    print("=" * 70)
    print("         GG WORKFLOW FRAMEWORK - QUICKSTART EXAMPLES")
    print("=" * 70)

    try:
        await example_1_simple_chain()
        await example_2_parallel()
        await example_3_transform()
        await example_4_with_hooks()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("- Check gg.md for full framework documentation")
        print("- Explore src/workflow/ for more node types")
        print("- Create your own custom nodes")
        print("- Integrate with Pantheon agents for AI-powered workflows")
        print()
        print("ZA GROKA. ZA GG. <3")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
