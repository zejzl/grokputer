"""
TOON utilities for Grokputer swarm efficiency.
Provides async encoding/decoding with token savings estimates.
"""

import asyncio
from typing import Any, Dict, Tuple

from toon_format import decode, encode  # python-toon library


class ToonDecodeError(Exception):
    """Raised when TOON decoding fails."""

    pass


async def encode_for_swarm(data: Dict[str, Any]) -> str:
    """
    Encode data to TOON format for swarm messages.
    Returns TOON string with ~30-60% token savings.
    """
    try:
        loop = asyncio.get_event_loop()
        toon_str = await loop.run_in_executor(None, encode, data)
        return toon_str
    except Exception as e:
        raise ToonDecodeError(f"TOON encode failed: {e}")


async def decode_from_swarm(toon_str: str) -> Dict[str, Any]:
    """
    Decode TOON string back to dict.
    Raises ToonDecodeError on failure.
    """
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, decode, toon_str)
        return data
    except Exception as e:
        raise ToonDecodeError(f"TOON decode failed: {e}")


async def estimate_savings(original: Dict[str, Any]) -> Tuple[str, float]:
    """
    Estimate TOON savings for data.
    Returns (toon_str, savings_percentage).
    """
    import json

    json_str = json.dumps(original, default=str)
    toon_str = await encode_for_swarm(original)
    json_len = len(json_str)
    toon_len = len(toon_str)
    savings = (1 - toon_len / json_len) * 100 if json_len > 0 else 0
    return toon_str, savings
