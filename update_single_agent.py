import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the function definition
pattern = r"def _run_single_agent_mode\(task: str, max_iterations: int, debug: bool, skip_boot: bool\):"
replacement = "async def _run_single_agent_mode(task: str, max_iterations: int, debug: bool, skip_boot: bool):"

content = re.sub(pattern, replacement, content, 1)

# Add await before boot()
pattern_boot = r"grokputer = Grokputer\(debug=debug\)\s*\n\s*if not skip_boot:\s*\n\s*grokputer\.boot\(\)"
replacement_boot = r"grokputer = Grokputer(debug=debug)\n    if not skip_boot:\n        await grokputer.boot()"

content = re.sub(pattern_boot, replacement_boot, content, 1)

# Add await before run_task()
pattern_run = r"grokputer\.boot\(\)\s*\n\s*grokputer\.run_task\(task=task, max_iterations=max_iterations\)"
replacement_run = r"await grokputer.boot()\n    await grokputer.run_task(task=task, max_iterations=max_iterations)"

content = re.sub(pattern_run, replacement_run, content, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated _run_single_agent_mode to async with awaits.")
