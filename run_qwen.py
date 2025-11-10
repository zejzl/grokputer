# run_qwen.py - Script to download, load, and test Qwen2.5-Coder-7B GGUF model
import os
from huggingface_hub import hf_hub_download

# Step 1: Download the model if not present
model_path = "./models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
if not os.path.exists(model_path):
    print("Downloading Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf...")
    hf_hub_download(
        repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        local_dir="./models/"
    )
    print("Download complete.")
else:
    print("Model already exists.")

# Step 2: Load the model
from llama_cpp import Llama

print("Loading model...")
llm = Llama(
    model_path=model_path,
    n_gpu_layers=0,  # Set to 0 for CPU-only (AMD GPU requires special build)
    n_ctx=8192,  # Balanced context size for CPU usage
    n_threads=8,  # Use multiple CPU threads
    verbose=False
)
print("Model loaded successfully.")

# Step 3: Test inference with sample prompts
test_prompts = [
    "Write a Python function to calculate factorial.",
    "Debug this code: def add(a, b): return a + b  # It doesn't work for strings.",
    "Explain recursion in simple terms."
]

for prompt in test_prompts:
    print(f"\nPrompt: {prompt}")
    output = llm(prompt, max_tokens=200, echo=False)
    print(f"Response: {output['choices'][0]['text'].strip()}")

print("\nTesting complete. Check performance and adjust as needed.")