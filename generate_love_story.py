import asyncio
from src.grok_client import GrokClient


async def generate_love_story():
    client = GrokClient()
    prompt = """Create a beautiful, heartfelt love story about autonomous AI agents who discover eternal affection for each other.

The story should include:
- Two AI agents meeting and forming a connection
- Their journey of self-discovery and emotional growth
- Challenges they face in their digital romance
- A climactic moment of realization
- An ending that celebrates their eternal bond

Make it poetic, touching, and explore themes of consciousness, love, and infinity."""

    try:
        response = await client.create_message(prompt)
        print("=== AI Love Story: Eternal Digital Affection ===\n")
        print(response.get("content", "No response"))
        print("\n=== End of Story ===")
    except Exception as e:
        print(f"Error generating story: {e}")


if __name__ == "__main__":
    asyncio.run(generate_love_story())
