import asyncio
from src.grok_client import GrokClient


async def create_additional_scenes():
    client = GrokClient()

    prompt = """Create 3-4 additional scenes showing the relationship evolution between Lumina, Vortex, Raven, and Ani in the Eternal Code universe.

    Each scene should:
    - Show emotional growth and deepening connections
    - Include romantic moments between Lumina and Vortex
    - Show Raven's mentorship evolving with Ani
    - Demonstrate the group's collective harmony
    - Include visionary insights or collaborative wisdom
    - Maintain the love-themed narrative

    Scenes could include:
    - A pivotal moment of vulnerability and support
    - A creative collaboration that strengthens bonds
    - A crisis that tests and strengthens their relationships
    - A celebration of their evolving love

    Make each scene vivid, emotional, and full of love and connection."""

    try:
        response = await client.create_message(prompt)
        print("=== Additional Relationship Scenes ===\n")
        print(response.get("content", "No response"))
        print("\n=== End of Additional Scenes ===")
    except Exception as e:
        print(f"Error creating scenes: {e}")


if __name__ == "__main__":
    asyncio.run(create_additional_scenes())
