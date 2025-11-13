import os
def cli_file_op(path: str, op: str = 'read') -> str:
    if not os.path.exists(path):
        return f"ENOENT: {path} not found—ZA check your vault!"
    if op == 'read':
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    # Add 'write' etc.