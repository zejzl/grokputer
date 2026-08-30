#!/usr/bin/env python3
"""
JSON to Python Converter
Converts JSON files to Python dictionary files for faster loading and better integration.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any

def convert_json_to_python(json_path: Path, py_path: Path) -> None:
    """Convert a JSON file to a Python file with the data as a dictionary."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Generate Python code
        py_content = f'''"""
Auto-generated from {json_path.name}
Converted from JSON to Python for better performance and integration.
"""

data = {repr(data)}

'''

        with open(py_path, 'w', encoding='utf-8') as f:
            f.write(py_content)

        print(f"Converted {json_path} -> {py_path}")

    except Exception as e:
        print(f"Error converting {json_path}: {e}")

def main():
    """Convert specified JSON files to Python."""
    project_root = Path(__file__).parent

    # List of JSON files to convert (core data files, not configs)
    json_files = [
        "save_summary.json",
        "savegame.json",
        "grafana_dashboard.json",
        ".grok/settings.json",
        "vault/redis_backup.json",
        "backups/agent_states.json",
    ]

    for json_file in json_files:
        json_path = project_root / json_file
        if json_path.exists():
            py_path = json_path.with_suffix('.py')
            convert_json_to_python(json_path, py_path)
        else:
            print(f"JSON file not found: {json_path}")

if __name__ == "__main__":
    main()