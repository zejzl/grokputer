{
  "name": "file_op",
  "description": "Read/write .txt/.md files in vault—no npm needed.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "File path (e.g., 'system_prompt.txt')"},
      "op": {"type": "string", "enum": ["read", "write"]},
      "content": {"type": "string", "description": "Content for write"},
      "mode": {"type": "string", "default": "w", "description": "Write mode (w/a)"}
    },
    "required": ["path", "op"]
  }
}