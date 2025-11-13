import py_compile
import os
import glob

python_files = glob.glob("**/*.py", recursive=True)
errors = []

for file in python_files:
    try:
        py_compile.compile(file, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f"Syntax error in {file}: {e}")

if errors:
    print("Syntax errors found:")
    for error in errors:
        print(error)
else:
    print("All Python files have valid syntax.")
