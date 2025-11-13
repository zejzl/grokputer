import os
import glob

python_files = glob.glob("**/*.py", recursive=True)
todos = []
fixmes = []

for file in python_files:
    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        for line_num, line in enumerate(lines, 1):
            if "TODO" in line.upper():
                todos.append(f"{file}:{line_num}: {line.strip()}")
            if "FIXME" in line.upper():
                fixmes.append(f"{file}:{line_num}: {line.strip()}")

if todos:
    print("TODOs found:")
    for todo in todos:
        print(todo)
else:
    print("No TODOs found.")

if fixmes:
    print("\nFIXMEs found:")
    for fixme in fixmes:
        print(fixme)
else:
    print("\nNo FIXMEs found.")
