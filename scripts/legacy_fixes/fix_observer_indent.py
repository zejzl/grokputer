import re

with open("src/agents/observer_agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the commented out Message block by commenting the indented lines or removing
# Pattern for the indented lines under commented msg
pattern_commented = r'# Send ready signal \(disabled for Phase 1 - coordinator doesn\'t handle this yet\)\s*\n\s*# msg = Message\(\s*\n\s*from_agent=self\.agent_id,\s*\n\s*to_agent="coordinator",\s*\n\s*message_type="agent_ready",\s*\n\s*content=\s*\{.*?\},\s*\n\s*priority=MessagePriority\.NORMAL\s*\n\s*\)\s*\n\s*# await self\.message_bus\.send\(msg\)'
replacement_commented = r'# Send ready signal (disabled for Phase 1 - coordinator doesn\'t handle this yet)\n# msg = Message(\n#     from_agent=self.agent_id,\n#     to_agent="coordinator",\n#     message_type="agent_ready",\n#     content={\n#         "agent_id": self.agent_id,\n#         "capabilities": ["observe_screen", "get_mouse_position", "get_screen_size"]\n#     },\n#     priority=MessagePriority.NORMAL\n# )\n# await self.message_bus.send(msg)'

content = re.sub(pattern_commented, replacement_commented, content, count=1)

with open("src/agents/observer_agent.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed indentation in observer_agent.py by properly commenting the disabled block.")
