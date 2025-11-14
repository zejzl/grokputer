import os
import glob

def clean_files():
    for pattern in ['*.py', '*.md']:
        for filepath in glob.glob(f'**/{pattern}', recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Remove lines containing the tags
                
                if len(cleaned) != len(lines):
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.writelines(cleaned)
                    print(f"Cleaned {filepath}")
            except Exception as e:
                print(f"Error cleaning {filepath}: {e}")

if __name__ == "__main__":
    clean_files()