with open("tests/test_core.py", "r") as f:
    content = f.read()

# Fix import
content = content.replace(
    "from src.core.message_bus import MessageBus  # Assume implemented",
    "from src.core.message_bus import MessageBus, Message",
)

# Fix the send line - assuming the exact string without indentation in the replace, but adjust for indentation
# The line is indented with 20 spaces (based on typical pytest code)
content = content.replace(
    '                    await bus.send("test_agent", {"type": "test"})',
    '                    msg = Message(\n                        from_agent="test_sender",\n                        to_agent="test_agent",\n                        message_type="test",\n                        content={"type": "test"}\n                    )\n                    await bus.send(msg)',
)

with open("tests/test_core.py", "w") as f:
    f.write(content)

print("Fixed test_core.py")
