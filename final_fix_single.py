import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Target the exact else block for single-agent
pattern = (
    r"else:\s*\n\s*    # Single-agent mode\s*\n\s*    _run_single_agent_mode\(task, max_iterations, debug, skip_boot\)"
)
replacement = r"else:\n            # Single-agent mode\n            asyncio.run(_run_single_agent_mode(task, max_iterations, debug, skip_boot))"

content = re.sub(pattern, replacement, content, count=1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

logger.info("Final fix: Wrapped single-agent call in asyncio.run with correct indentation.")
