import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the indentation in interactive mode for single agent
# Look for the messed up part around grokputer.run_task
pattern_mess = r"grokputer = Grokputer\(debug=debug\)\s*\n\s*if not skip_boot:\s*\n\s*await grokputer\.boot\(\)\s*\n\s*grokputer\.run\(task=task, max_iterations=max_iterations\)"
replacement_mess = r"grokputer = Grokputer(debug=debug)\n            if not skip_boot:\n                await grokputer.boot()\n            asyncio.run(grokputer.run_task(task=task, max_iterations=max_iterations))"

content = re.sub(pattern_mess, replacement_mess, content, count=1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed indentation error in interactive mode single agent section.")
