import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("autonomous.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the unterminated string in KeyboardInterrupt block
content = re.sub(
    r'console\.print\("(\s*)(\[green\]Daemon stopped by user\.\[/green\]"?\)',
    r'console.print("\\n\1\2")',
    content,
    flags=re.DOTALL,
)

# Ensure proper closure
content = content.replace('console.print("', 'console.print("\\n') if "Daemon stopped" in content else content

with open("autonomous.py", "w", encoding="utf-8") as f:
    f.write(content)

logger.info("Robust syntax fix applied.")
