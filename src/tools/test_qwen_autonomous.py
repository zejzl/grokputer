#!/usr/bin/env python3
"""Test Qwen with autonomous.py analysis."""
import os
from llama_cpp import Llama

# Load the model
model_path = "./models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
print("Loading Qwen model with balanced context (8192 tokens)...")
llm = Llama(
    model_path=model_path,
    n_gpu_layers=0,  # CPU-only for AMD GPU compatibility
    n_ctx=8192,  # Balanced for CPU usage
    n_threads=8,  # Multi-threaded CPU processing
    verbose=False
)
print("Model loaded successfully.\n")

# Read autonomous.py
with open("autonomous.py", "r", encoding="utf-8") as f:
    code_content = f.read()

# Create prompt
prompt = f"""You are a senior Python developer. Analyze the following code from autonomous.py and suggest specific improvements.

Focus on:
1. Code quality and best practices
2. Error handling and edge cases
3. Performance optimizations
4. Security considerations
5. User experience improvements

Here's the code:

```python
{code_content}
```

Provide 3-5 concrete, actionable improvements with code examples where applicable."""

print("Analyzing autonomous.py...")
print("=" * 80)

# Generate response
output = llm(
    prompt,
    max_tokens=2048,
    temperature=0.7,
    top_p=0.9,
    echo=False
)

response = output['choices'][0]['text'].strip()
print(response)
print("\n" + "=" * 80)
print("Analysis complete!")
