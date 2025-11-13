import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Robust replacement for the single-agent call using regex to match indentation
pattern = r"\s*_run_single_agent_mode\s*\(task, max_iterations, debug, skip_boot\)"
replacement = "            asyncio.run(_run_single_agent_mode(task, max_iterations, debug, skip_boot))"

content = re.sub(pattern, replacement, content, count=1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

logger.info("Robustly replaced the single-agent call with asyncio.run wrap using regex.")
