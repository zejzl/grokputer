#!/usr/bin/env python3
"""
Quick API connection test script
"""
import asyncio
import sys
import os

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(__file__))

from src.grok_client import GrokClient
from src.model_client import ModelClientFactory


async def test_grok():
    print("Testing Grok API connection...")
    grok_key = os.getenv("XAI_API_KEY", "")
    if not grok_key:
        print("XAI_API_KEY not found, skipping Grok test")
        return False
    client = ModelClientFactory.create_client("grok", grok_key, "grok-4-fast-reasoning")
    result = await client.test_connection()
    print(f"Grok API test result: {result}")
    return result


async def test_model_factory():
    print("Testing ModelClientFactory connections...")

    # Test Grok
    try:
        grok_client = ModelClientFactory.create_client("grok", os.getenv("XAI_API_KEY", ""), "grok-4-fast-reasoning")
        grok_result = await grok_client.test_connection()
        print(f"ModelFactory Grok test: {grok_result}")
    except Exception as e:
        print(f"ModelFactory Grok error: {e}")

    # Test Claude if key exists
    claude_key = os.getenv("ANTHROPIC_API_KEY", "")
    if claude_key:
        try:
            claude_client = ModelClientFactory.create_client("claude", claude_key, "claude-3-sonnet-20240229")
            claude_result = await claude_client.test_connection()
            print(f"Claude API test: {claude_result}")
        except Exception as e:
            print(f"Claude API error: {e}")
    else:
        print("Claude API key not found, skipping test")

    # Test Gemini if key exists
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            gemini_client = ModelClientFactory.create_client("gemini", gemini_key, "gemini-1.5-flash")
            gemini_result = await gemini_client.test_connection()
            print(f"Gemini API test: {gemini_result}")
        except Exception as e:
            print(f"Gemini API error: {e}")
    else:
        print("Gemini API key not found, skipping test")

    # Test Ollama (local)
    try:
        ollama_client = ModelClientFactory.create_client("ollama", "", "llama2")
        ollama_result = await ollama_client.test_connection()
        print(f"Ollama API test: {ollama_result}")
    except Exception as e:
        print(f"Ollama API error: {e}")


async def main():
    await test_grok()
    await test_model_factory()


if __name__ == "__main__":
    asyncio.run(main())
