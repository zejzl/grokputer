import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the call to _run_single_agent_mode in the else block of main
# Use a more flexible pattern for the else block
pattern = r"(else:\s*\n\s*    # Single-agent mode\s*\n\s*    )_run_single_agent_mode"
replacement = r"\1asyncio.run("

content = re.sub(pattern, replacement, content, count=1)

# Close the run
pattern_close = r"_run_single_agent_mode\(task, max_iterations, debug, skip_boot\)(.*)"
replacement_close = r"_run_single_agent_mode(task, max_iterations, debug, skip_boot)\1)"

content = re.sub(pattern_close, replacement_close, content, count=1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Precisely wrapped _run_single_agent_mode in asyncio.run in main else block.")
