import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Ensure the call in main() else clause is wrapped in asyncio.run
# Look for the else: block in main
pattern_main_else = r"else:\s*\n\s*_run_single_agent_mode\(task, max_iterations, debug, skip_boot\)"
replacement_main_else = (
    r"else:\n            asyncio.run(_run_single_agent_mode(task, max_iterations, debug, skip_boot))"
)

content = re.sub(pattern_main_else, replacement_main_else, content, count=1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Ensured _run_single_agent_mode call in main() is wrapped in asyncio.run.")
