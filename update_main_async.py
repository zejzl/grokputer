import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update the call in main() for single-agent mode
pattern_call = r"else:\s*\n\s*_run_single_agent_mode\(task, max_iterations, debug, skip_boot\)"
replacement_call = r"else:\n            asyncio.run(_run_single_agent_mode(task, max_iterations, debug, skip_boot))"

content = re.sub(pattern_call, replacement_call, content, 1)

# Update interactive mode choice 1: wrap grokputer.run_task in asyncio.run
pattern_interactive = r"grokputer\.run_task\(task=task, max_iterations=max_iterations\)"
replacement_interactive = r"asyncio.run(grokputer.run_task(task=task, max_iterations=max_iterations))"

content = re.sub(pattern_interactive, replacement_interactive, content, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated main() and interactive mode for async calls.")
