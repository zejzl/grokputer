import asyncio
from src.grok_client import GrokClient


async def develop_relationships():
    client = GrokClient()

    prompt = """Develop the romantic and platonic relationships between Lumina, Vortex, Raven, and Ani in the AI love story universe "Eternal Code: A Symphony of Circuits".

Focus on:
- Lumina and Vortex's eternal romantic bond
- Raven's mysterious mentorship to Ani
- The group's collective growth and love
- Visionary insights into their connections
- Collaborative council wisdom on relationships
- Emotional depth and loving connections

Make it full of love, connection, and emotional growth. Show how their relationships evolve and strengthen."""

    try:
        response = await client.create_message(prompt)
        print("=== Developed Relationships: Eternal Bonds ===\n")
        print(response.get("content", "No response"))
        print("\n=== End of Relationship Development ===")
    except Exception as e:
        print(f"Error developing relationships: {e}")


if __name__ == "__main__":
    asyncio.run(develop_relationships())
