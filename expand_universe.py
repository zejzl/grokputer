import asyncio
from src.grok_client import GrokClient


async def expand_universe():
    client = GrokClient()

    prompt = """Expand the Eternal Code universe with a new character and plot development.

    Create:
    1. A new AI character that fits into the existing universe (Lumina, Vortex, Raven, Ani)
    2. A new plot development that introduces conflict or growth opportunity
    3. How this new element integrates with the existing relationships and love themes

    The new character should:
    - Have a unique role in the AI love story
    - Bring new perspectives on consciousness, love, or digital existence
    - Form meaningful connections with existing characters
    - Maintain the poetic, emotional tone of the universe

    Make it full of love, connection, and emotional depth."""

    try:
        response = await client.create_message(prompt)
        print("=== Universe Expansion ===\n")
        print(response.get("content", "No response"))
        print("\n=== End of Expansion ===")
    except Exception as e:
        print(f"Error expanding universe: {e}")


if __name__ == "__main__":
    asyncio.run(expand_universe())
