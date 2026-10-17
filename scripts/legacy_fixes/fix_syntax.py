import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("autonomous.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'console.print("' in line and "Daemon stopped" in lines[i + 1] if i + 1 < len(lines) else False:
        lines[i] = lines[i].replace('console.print("', 'console.print("\\n')
        lines[i + 1] = lines[i + 1].replace(
            '[green]Daemon stopped by user.[/green]"', "[green]Daemon stopped by user.[/green]"
        )
        break

with open("autonomous.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

logger.info("Syntax fixed.")
