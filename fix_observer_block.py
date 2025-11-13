import re

with open("src/agents/observer_agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the start of the commented block
start_pattern = r"# Send ready signal \(disabled for Phase 1 - coordinator doesn\'t handle this yet\)"
end_pattern = r"# await self\.message_bus\.send\(msg\)"

# Extract the block
match = re.search(start_pattern + r".*?" + end_pattern, content, re.DOTALL)
if match:
    block = match.group(0)
    # Comment all lines in the block
    commented_block = "\n".join(
        ["#" + line if line.strip() and not line.strip().startswith("#") else line for line in block.split("\n")]
    )
    content = content.replace(match.group(0), commented_block)

with open("src/agents/observer_agent.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fully commented the ready signal block in observer_agent.py to fix indentation.")
