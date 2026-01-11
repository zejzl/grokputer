async def toon_encode_decode_demo():
    try:
        from src.utils.toon_utils import encode_for_swarm, decode_from_swarm  # Assuming path from grok.md
        data = {"handoffs": 5, "agents": ["obs", "act"]}
        toon = await encode_for_swarm(data)
        decoded = await decode_from_swarm(toon)
        savings = (1 - len(str(toon)) / len(str(data))) * 100
        return f"TOON Demo: Encoded {data} to '{toon}' (Savings: {savings:.1f}%). Decoded: {decoded == data}"
    except ImportError:
        return "TOON utils not available; install toon-python via pip."

print(toon_encode_decode_demo())