#!/usr/bin/env python3

from pathlib import Path
import re
from typing import Dict, Any, List

def parse_swarm_examples(content: str) -> List[Dict[str, Any]]:
    examples = []

    start_idx = content.find('Command Simulated')
    if start_idx == -1:
        print("No 'Command Simulated' found")
        return examples
    content = content[start_idx:]

    sections = re.split(r'(?=Command Simulated)', content)
    print(f"Found {len(sections)} sections")

    for i, section in enumerate(sections):
        if not section.strip():
            continue

        example = {}

        task_match = re.search(r'Command Simulated: (.+?)\n', section, re.IGNORECASE)
        if task_match:
            example['task'] = task_match.group(1).strip()

        time_match = re.search(r'Completed in (\d+\.?\d*)s', section)
        if time_match:
            example['execution_time'] = float(time_match.group(1))

        msg_match = re.search(r'Messages sent: (\d+)', section)
        if msg_match:
            example['message_count'] = int(msg_match.group(1))

        agent_match = re.search(r'Agents?: (\d+)', section, re.IGNORECASE)
        if agent_match:
            example['agent_count'] = int(agent_match.group(1))

        if example.get('task'):
            examples.append(example)
            print(f"Example {len(examples)}: {example}")

    return examples

if __name__ == "__main__":
    try:
        content = Path('../docs/grokputer_swarm_examples.md').read_text()
        print(f"File loaded, length: {len(content)}")
        examples = parse_swarm_examples(content)
        print(f"Total examples parsed: {len(examples)}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()