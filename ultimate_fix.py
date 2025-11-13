import re

with open("autonomous.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the except block and replace the entire thing
pattern = r'except KeyboardInterrupt:.*?r\.set\("daemon_stopped", "true"\)'
replacement = """except KeyboardInterrupt:
    console.print("\\n[green]Daemon stopped by user.[/green]")
    if r:
        r.set("daemon_stopped", "true")"""

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open("autonomous.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Ultimate fix applied to except block.")
