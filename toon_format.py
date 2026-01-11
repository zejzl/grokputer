"""
TOON Format Fallback Implementation

Simple encode/decode functions for TOON format when the python-toon library is not available.
Provides basic JSON-based encoding/decoding as a fallback.
"""

import json
from typing import Any, Dict


def encode(data: Dict[str, Any]) -> str:
    """
    Encode data to TOON format (fallback: JSON with TOON marker).

    Args:
        data: Dictionary to encode

    Returns:
        Encoded string
    """
    # Add TOON marker for identification
    toon_data = {
        "_format": "TOON_FALLBACK",
        "_version": "1.0",
        "data": data
    }
    return json.dumps(toon_data, default=str, separators=(',', ':'))


def decode(toon_str: str) -> Dict[str, Any]:
    """
    Decode TOON format string (fallback: JSON parsing).

    Args:
        toon_str: TOON encoded string

    Returns:
        Decoded dictionary
    """
    try:
        parsed = json.loads(toon_str)

        # Check if it's our fallback format
        if isinstance(parsed, dict) and parsed.get("_format") == "TOON_FALLBACK":
            return parsed.get("data", {})

        # Assume it's regular JSON
        return parsed

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid TOON format: {e}")


def is_toon_format(data_str: str) -> bool:
    """
    Check if string is in TOON format.

    Args:
        data_str: String to check

    Returns:
        True if TOON format
    """
    try:
        parsed = json.loads(data_str)
        return isinstance(parsed, dict) and parsed.get("_format") == "TOON_FALLBACK"
    except:
        return False


# Try to import the real TOON library if available
try:
    from toon_format import encode as real_encode, decode as real_decode

    # Override with real implementations
    encode = real_encode
    decode = real_decode

    print("Using real TOON library")

except ImportError:
    print("Using TOON fallback implementation (JSON-based)")