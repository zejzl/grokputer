#!/usr/bin/env python3
"""Mass fix: Add 'from __future__ import annotations' to all Python files that need it."""

import os
import re
from pathlib import Path

def needs_fix(content):
    """Check if file needs the future import."""
    has_typing = bool(re.search(r'from typing import|^import typing', content, re.MULTILINE))
    has_future = 'from __future__ import annotations' in content
    return has_typing and not has_future

def fix_file(filepath):
    """Add future import to a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not needs_fix(content):
        return False
    
    lines = content.split('\n')
    
    # Find where to insert (after shebang, docstring, but before imports)
    insert_pos = 0
    in_docstring = False
    docstring_char = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip shebang
        if i == 0 and stripped.startswith('#!'):
            insert_pos = 1
            continue
        
        # Handle docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                if stripped.count(docstring_char) >= 2:
                    # Single-line docstring
                    insert_pos = i + 1
                else:
                    in_docstring = True
        else:
            if docstring_char in line:
                in_docstring = False
                insert_pos = i + 1
                continue
        
        # Stop at first import
        if stripped.startswith('import ') or stripped.startswith('from '):
            break
        
        if not in_docstring and stripped and not stripped.startswith('#'):
            insert_pos = i
            break
    
    # Insert the future import
    lines.insert(insert_pos, 'from __future__ import annotations')
    if insert_pos < len(lines) - 1 and lines[insert_pos + 1].strip():
        lines.insert(insert_pos + 1, '')  # Add blank line
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return True

def main():
    """Fix all Python files in the current directory."""
    root = Path('.')
    count = 0
    
    for py_file in root.rglob('*.py'):
        try:
            if fix_file(py_file):
                print(f'Fixed: {py_file}')
                count += 1
        except Exception as e:
            print(f'Error fixing {py_file}: {e}')
    
    print(f'\nFixed {count} files')

if __name__ == '__main__':
    main()
