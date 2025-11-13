import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Direct replacement for the single-agent call line
old_line = "            _run_single_agent_mode(task, max_iterations, debug, skip_boot)"
new_line = "            asyncio.run(_run_single_agent_mode(task, max_iterations, debug, skip_boot))"

content = content.replace(old_line, new_line)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

logger.info("Directly replaced the single-agent call with asyncio.run wrap.")
