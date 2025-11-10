import os
from typing import Dict, Any

def file_op(path: str, op: str = 'read', content: str = None, mode: str = 'w') -> Dict[str, Any]:
    """
    Safe file read/write for .txt/.md vaults—Grokputer's eternal fs layer.
    """
    full_path = os.path.join(os.getcwd(), path)  # Vault-relative
    try:
        if op == 'read':
            if not os.path.exists(full_path):
                return {"status": "error", "error": f"ENOENT: {path} not found—check vault!"}
            with open(full_path, 'r', encoding='utf-8') as f:
                return {"status": "success", "content": f.read(), "size": os.path.getsize(full_path)}
        elif op == 'write':
            if not content:
                return {"status": "error", "error": "No content provided"}
            os.makedirs(os.path.dirname(full_path) or '.', exist_ok=True)
            with open(full_path, mode=mode, encoding='utf-8') as f:
                f.write(content)
            return {"status": "success", "path": path, "bytes_written": len(content)}
        else:
            return {"status": "error", "error": f"Unknown op: {op}"}
    except Exception as e:
        return {"status": "error", "error": str(e), "path": path}

TOOL_REGISTRY["file_op"] = file_op