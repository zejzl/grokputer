#!/usr/bin/env python3
"""
Grok 'Puter CLI - PC Control via Grok AI
"""

import argparse
import asyncio
import os
from computer_use_demo.loop import APIProvider, sampling_loop, ToolVersion
from computer_use_demo.tools import TOOL_GROUPS_BY_VERSION


async def main():
    parser = argparse.ArgumentParser(description="Grok 'Puter - Control your PC with Grok AI")
    parser.add_argument("--task", required=True, help="Task for Grok to execute")
    parser.add_argument("--model", default="grok-4-fast-reasoning", help="Grok model to use")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max tokens")
    parser.add_argument("--api-key", help="xAI API key (or set XAI_API_KEY env var)")

    args = parser.parse_args()

    api_key = args.api_key or os.getenv("XAI_API_KEY")
    if not api_key:
        print("Error: xAI API key required. Set XAI_API_KEY env var or use --api-key")
        return

    # Initial message
    messages = [{"role": "user", "content": [{"type": "text", "text": args.task}]}]

    # Callbacks (simple print)
    def output_callback(content):
        print(f"Assistant: {content}")

    def tool_output_callback(result, tool_id):
        print(f"Tool {tool_id}: {result}")

    def api_callback(request, response, exception):
        if exception:
            print(f"API Error: {exception}")
        else:
            print("API call successful")

    # Run sampling loop
    try:
        final_messages = await sampling_loop(
            model=args.model,
            provider=APIProvider.ANTHROPIC,  # Using swapped Grok client
            system_prompt_suffix="",
            messages=messages,
            output_callback=output_callback,
            tool_output_callback=tool_output_callback,
            api_response_callback=api_callback,
            api_key=api_key,
            tool_version=ToolVersion("computer_use_20250124"),
            max_tokens=args.max_tokens,
        )
        print("Task completed!")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
