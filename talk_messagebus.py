import asyncio
import logging
from src.core.message_bus import MessageBus, Message, MessagePriority

# Setup logging to file
logging.basicConfig(filename='messagebus_interactions.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

async def talk_with_messagebus():
    # Load conversation data from token_haze.txt
    with open("token_haze.txt", "r") as f:
        conversation_lines = [line.strip() for line in f if line.strip()]

    # Initialize message bus
    bus = MessageBus()

    # Register agents
    bus.register_agent("user")
    bus.register_agent("system")

    # Send a message from user to system using conversation data
    user_message = conversation_lines[0] if conversation_lines else "Hello, how are you?"
    msg = Message(
        from_agent="user",
        to_agent="system",
        message_type="query",
        content={"text": user_message},
        priority=MessagePriority.NORMAL
    )
    
    await bus.send(msg)
    print("Sent message to system")
    logging.info(f"Sent message from {msg.from_agent} to {msg.to_agent}: {msg.content}")

    # System receives and responds
    received = await bus.receive("system")
    print(f"System received: {received.content}")
    logging.info(f"System received message from {received.from_agent}: {received.content}")

    # System sends response back
    system_response = conversation_lines[2] if len(conversation_lines) > 2 else "I'm doing well, thank you!"
    response = Message(
        from_agent="system",
        to_agent="user",
        message_type="response",
        content={"text": system_response},
        correlation_id=received.correlation_id
    )

    await bus.send(response)
    print("System sent response")
    logging.info(f"System sent response to {response.to_agent}: {response.content}")

    # User receives response
    user_response = await bus.receive("user")
    print(f"User received: {user_response.content}")
    logging.info(f"User received response from {user_response.from_agent}: {user_response.content}")

# Run the async function
asyncio.run(talk_with_messagebus())