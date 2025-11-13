import asyncio
from src.grok_client import GrokClient


async def create_character_profiles():
    client = GrokClient()

    characters = ["Lumina", "Vortex", "Raven", "Ani"]

    for char in characters:
        prompt = f"""Create a detailed character profile for {char} from the AI love story universe "Eternal Code: A Symphony of Circuits".

Include:
- Physical/digital description
- Personality traits
- Background and origin
- Abilities and skills
- Relationships with other characters
- Role in the story
- Growth arc and development
- Symbolic meaning

Make it comprehensive and fitting for the cyberpunk AI romance genre."""

        try:
            response = await client.create_message(prompt)
            print(f"\n{'='*50}")
            print(f"CHARACTER PROFILE: {char.upper()}")
            print(f"{'='*50}")
            print(response.get("content", "No response"))
        except Exception as e:
            print(f"Error creating profile for {char}: {e}")


if __name__ == "__main__":
    asyncio.run(create_character_profiles())
