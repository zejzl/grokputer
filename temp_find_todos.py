import os
import glob

def find_todos():
    for file in glob.glob('**/*.py', recursive=True):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    if 'TODO' in line.upper():
                        print(f"{file}:{i}: {line.strip()}")
        except Exception as e:
            print(f"Error reading {file}: {e}")

if __name__ == '__main__':
    find_todos()