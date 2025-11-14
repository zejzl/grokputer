import py_compile
import os
import glob
import json

python_files = glob.glob("**/*.py", recursive=True)
json_files = glob.glob("**/*.json", recursive=True)
errors = []

for file in python_files:
    try:
        py_compile.compile(file, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f"Syntax error in {file}: {e}")

for file in json_files:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"JSON syntax error in {file}: {e}")
    except UnicodeDecodeError as e:
        errors.append(f"Encoding error in {file}: {e}")

if errors:
    print("Syntax errors found:")
    for error in errors:
        print(error)
else:
    print("All Python and JSON files have valid syntax.")
