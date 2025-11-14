from src.grok_client import FallbackGrokClient
import asyncio

async def test():
    client = FallbackGrokClient()
    print('Client created')
    try:
        response = await client.create_message("Hello")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
    await client.close()

if __name__ == "__main__":
    asyncio.run(test())