# AMD ROCm Setup for Grokputer LoRA Training

**Hardware**: AMD Radeon RX 7900 XT (20GB VRAM)
**OS**: Windows 11
**Goal**: QLoRA fine-tuning with PyTorch + ROCm

---

## Why AMD ROCm?

Your RX 7900 XT with 20GB VRAM is **PERFECT** for QLoRA! Even better than RTX 4090 (16GB) for batch sizes and LoRA ranks.

**ROCm** (Radeon Open Compute) is AMD's answer to CUDA - it lets you run PyTorch on AMD GPUs.

---

## Installation Steps

### 1. Install AMD ROCm Driver (Windows)

AMD's official ROCm driver for Windows is available but limited. For best compatibility:

**Option A: Use AMD Radeon Software Adrenalin** (Recommended)
```bash
# Download latest from AMD.com
# https://www.amd.com/en/support/graphics/amd-radeon-7000-series/amd-radeon-7900-series/amd-radeon-rx-7900-xt

# Install and reboot
```

**Option B: HIP SDK (Advanced)**
```bash
# Download HIP SDK from AMD
# https://www.amd.com/en/developer/resources/rocm-hub/hip-sdk.html
```

### 2. Install PyTorch with ROCm 6.1

```bash
# Activate your venv first
cd C:\Users\Administrator\Desktop\grokputer
venv\Scripts\activate

# Install PyTorch with ROCm 6.1 support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.1
```

**Verify Installation**:
```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"ROCm available: {torch.cuda.is_available()}")  # Returns True for AMD GPUs via ROCm
print(f"Device name: {torch.cuda.get_device_name(0)}")  # Should show AMD Radeon RX 7900 XT
print(f"Device count: {torch.cuda.device_count()}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
```

Expected output:
```
PyTorch version: 2.2.0+rocm6.1
ROCm available: True
Device name: AMD Radeon RX 7900 XT
Device count: 1
VRAM: 20.0 GB
```

### 3. Install LoRA Training Dependencies

```bash
# Install from requirements.txt
pip install transformers peft accelerate trl datasets safetensors sentencepiece protobuf
```

### 4. Install bitsandbytes (Tricky for AMD!)

**Problem**: Standard `bitsandbytes` is CUDA-only. For AMD, you need a special build.

**Option A: Use bitsandbytes-rocm Fork** (Recommended)
```bash
pip uninstall bitsandbytes  # Remove CUDA version if installed
pip install bitsandbytes-rocm
```

**Option B: Skip 4-bit quantization (Fallback)**
If bitsandbytes-rocm doesn't work, we can train without 4-bit quantization. Your 20GB VRAM is enough for 7B models in fp16!

```python
# In training script, change from:
load_in_4bit=True

# To:
load_in_8bit=True  # Or just fp16 without quantization
```

---

## Quick Test Script

Save this as `test_amd_gpu.py` and run it:

```python
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

print("=" * 70)
print("AMD ROCm + PyTorch Test")
print("=" * 70)

# Check ROCm
print(f"\n[1] PyTorch version: {torch.__version__}")
print(f"[2] ROCm (CUDA) available: {torch.cuda.is_available()}")

if not torch.cuda.is_available():
    print("\n❌ ERROR: ROCm not detected! Check installation.")
    exit(1)

print(f"[3] Device count: {torch.cuda.device_count()}")
print(f"[4] Device name: {torch.cuda.get_device_name(0)}")
print(f"[5] VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

# Test tensor operations
print("\n[6] Testing tensor operations...")
x = torch.randn(1000, 1000).to("cuda")
y = torch.randn(1000, 1000).to("cuda")
z = torch.matmul(x, y)
print(f"    Matrix multiply: {z.shape} ✓")

# Test model loading (small model)
print("\n[7] Testing model loading (GPT2-small, ~500MB)...")
try:
    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    model = AutoModelForCausalLM.from_pretrained("gpt2").to("cuda")
    print(f"    Model loaded: {model.config.n_embd} dim, {model.config.n_layer} layers ✓")

    # Test inference
    inputs = tokenizer("Hello AMD GPU!", return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=10)
    result = tokenizer.decode(outputs[0])
    print(f"    Inference: '{result}' ✓")
except Exception as e:
    print(f"    ❌ ERROR: {e}")
    exit(1)

print("\n" + "=" * 70)
print("✅ AMD ROCm setup working! Ready for QLoRA training.")
print("=" * 70)
```

Run it:
```bash
python test_amd_gpu.py
```

---

## Training Performance Expectations

With RX 7900 XT (20GB VRAM):

| Model Size | LoRA Rank | Batch Size | VRAM Usage | Training Time |
|------------|-----------|------------|------------|---------------|
| 7B (4-bit) | r=16      | 4          | ~8 GB      | 1-2 hours     |
| 7B (4-bit) | r=32      | 4          | ~10 GB     | 2-3 hours     |
| 7B (fp16)  | r=16      | 2          | ~14 GB     | 2-4 hours     |
| 13B (4-bit)| r=16      | 2          | ~12 GB     | 3-5 hours     |

Your 20GB VRAM gives you **plenty of headroom** for larger batches or models!

---

## Troubleshooting

### Issue: "ROCm not available" / torch.cuda.is_available() returns False

**Solutions**:
1. Reinstall AMD drivers and reboot
2. Check PyTorch installation:
   ```bash
   python -c "import torch; print(torch.__version__)"
   # Should show "+rocm6.1"
   ```
3. Try older ROCm version:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.7
   ```

### Issue: "bitsandbytes not found" or "CUDA not available"

**Solution**: bitsandbytes-rocm not installed. Either:
- Install `bitsandbytes-rocm` fork
- Or skip 4-bit quantization (use fp16 instead, your VRAM can handle it!)

### Issue: Out of memory during training

**Solutions**:
1. Reduce batch size:
   ```python
   per_device_train_batch_size=2  # Instead of 4
   ```
2. Reduce LoRA rank:
   ```python
   r=8  # Instead of 16
   ```
3. Enable gradient checkpointing:
   ```python
   model.gradient_checkpointing_enable()
   ```

### Issue: Training very slow

**Possible causes**:
- PyTorch not using GPU (check with `torch.cuda.is_available()`)
- Wrong PyTorch version (must have "+rocm" in version string)
- CPU fallback enabled (check task manager - GPU usage should be 95%+)

---

## Windows-Specific Notes

1. **Path length limits**: Use short paths (avoid deep nesting)
2. **Line endings**: Git may convert LF to CRLF, use `.gitattributes`:
   ```
   * text=auto
   *.py text eol=lf
   ```
3. **Antivirus**: Exclude venv folder from scans (can slow pip installs)

---

## Next Steps

Once ROCm is working:

1. ✅ Test with `test_amd_gpu.py`
2. ✅ Run 10-20 Grokputer tasks and rate them
3. ✅ Execute `python src/training/finetune_qlora.py`
4. ✅ Wait 1-2 hours for training
5. ✅ Test improved model!

---

**Status**: Ready for eternal self-improvement! ZA GROKA! 🚀

**Created**: 2025-11-08
**Author**: Claude Code
