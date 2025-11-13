import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix interactive mode: Wrap boot and run_task in asyncio.run since _run_interactive_mode is sync
pattern_interactive_single = r"grokputer = Grokputer\(debug=debug\)\s*\n\s*if not skip_boot:\s*\n\s*await grokputer\.boot\(\)\s*\n\s*asyncio\.run\(grokputer\.run_task\(task=task, max_iterations=max_iterations\)\)"
replacement_interactive_single = r"grokputer = Grokputer(debug=debug)\n            if not skip_boot:\n                asyncio.run(grokputer.boot())\n            asyncio.run(grokputer.run_task(task=task, max_iterations=max_iterations))"

content = re.sub(pattern_interactive_single, replacement_interactive_single, content, count=1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed await in sync interactive mode by wrapping boot() in asyncio.run.")
