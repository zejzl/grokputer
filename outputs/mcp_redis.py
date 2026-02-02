"""
Custom MCP-Redis Integration Script for Grokputer
Description: Discovers tools from MCP server, saves discovery results to Redis state,
and tests retrieval. Integrates with db_config.py and MCP endpoint.
Usage: python outputs/mcp_redis.py [discover|test|full]
"""
from __future__ import annotations

import asyncio
import aiohttp
import json
from datetime import datetime
from db_config import save_state, retrieve_state, init_redis
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MCP_URL = "http://localhost:8000"
STATE_KEY = "grokputer:state:mcp_redis_test"


async def discover_mcp_tools(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Discover tools from MCP server."""
    try:
        async with session.get(f"{MCP_URL}/tools") as resp:
            if resp.status == 200:
                tools = await resp.json()
                logger.info(f"Discovered {len(tools)} MCP tools")
                return tools
            else:
                logger.error(f"MCP discovery failed: {resp.status}")
                return []
    except Exception as e:
        logger.error(f"Discovery error: {e}")
        return []


def save_discovery_to_redis(tools: List[Dict[str, Any]]):
    """Save discovered tools to Redis state."""
    data = {"timestamp": datetime.now().isoformat(), "tools": tools, "count": len(tools), "mcp_url": MCP_URL}
    success = save_state(STATE_KEY, data, ttl=3600)
    if success:
        logger.info(f"Saved MCP discovery to Redis: {STATE_KEY}")
    return success


def retrieve_and_verify():
    """Retrieve state from Redis and verify."""
    state = retrieve_state(STATE_KEY)
    if state:
        logger.info(f"Retrieved state: {len(state['tools'])} tools")
        logger.info(f"Sample tool: {state['tools'][0] if state['tools'] else 'None'}")
        return state
    else:
        logger.warning("No state found in Redis")
        return None


async def run_discover():
    """Run discovery and save."""
    init_redis()
    async with aiohttp.ClientSession() as session:
        tools = await discover_mcp_tools(session)
        save_discovery_to_redis(tools)
        retrieve_and_verify()


async def run_test():
    """Full test: discover, save, retrieve."""
    await run_discover()
    # Simulate agent use
    logger.info("[TEST] Simulating agent query...")
    state = retrieve_and_verify()
    if state and len(state["tools"]) > 0:
        logger.info("[SUCCESS] MCP-Redis integration verified!")
        return True
    else:
        logger.error("[FAIL] Test failed")
        return False


async def run_full():
    """Full integration test with multiple cycles."""
    for i in range(3):
        logger.info(f"[CYCLE {i+1}] Running test...")
        success = await run_test()
        if not success:
            break
        await asyncio.sleep(1)  # Simulate delay
    logger.info("[FULL TEST] Complete.")


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    if mode == "discover":
        asyncio.run(run_discover())
    elif mode == "test":
        asyncio.run(run_test())
    elif mode == "full":
        asyncio.run(run_full())
    else:
        print("Usage: python mcp_redis.py [discover|test|full]")
