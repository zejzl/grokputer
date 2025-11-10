# LoRA Implementation Plan for Grokputer

## Overview
This plan implements Low-Rank Adaptation (LoRA) for fine-tuning Grok-1 (or compatible models like Llama-3) to enhance Grokputer agents. Based on `lora.md`, it focuses on efficient adaptation for tasks like agent coordination, screenshot analysis, and code generation. Uses PEFT library for 90% parameter reduction, async compatibility, and integration with TOON for compact payloads.

**Key Benefits**:
- Train only 0.1-1% of parameters.
- Faster inference (1.5-2x), lower costs ($5-20/train).
- Task-specific adapters (e.g., for Coordinator, Observer).

**Timeline**: 2-3 days. **Requirements**: GPU (RTX 3090+), CUDA 11.8+. **Fit in Project**: Phase 2/3 enhancement (advanced swarm patterns).

## High-Level Phases
1. **Setup & Data (High Priority)**: Environment and dataset prep (4-6 hours).
2. **Model & Training (High/Medium)**: Load, train, evaluate (10-15 hours).
3. **Integration & Optimization (Medium/Low)**: Deploy in Grokputer, refine (6-8 hours).
4. **Docs & Testing (Low)**: Ensure reproducibility (2-3 hours).

## Active Todo List
Todos are tracked via the project's todo system. Current status as of 2025-11-08:

- **🔴 id: lora-setup-env** (Status: in_progress)  
  Content: Set up development environment for LoRA: Install necessary libraries (peft, transformers, torch, datasets, accelerate, bitsandbytes). Ensure GPU availability (CUDA 11.8+). Create a virtual env or use Docker.  
  Next Action: Run `pip install -r requirements-lora.txt`. Test: `import torch; print(torch.cuda.is_available())`.  
  *Dependencies*: See `requirements-lora.txt`.

- **🔴 id: lora-data-prep** (Status: pending)  
  Content: Prepare dataset: Use or create a fine-tuning dataset (e.g., instruction-response pairs relevant to Grokputer tasks like agent coordination, screenshot analysis). Format as JSONL or HuggingFace Dataset. Split into train/val (80/20). Tokenize with Grok tokenizer.  
  Priority: high  
  Code Snippet:  
  ```python
  from datasets import Dataset, load_dataset
  from transformers import AutoTokenizer

  data = load_dataset("json", data_files="grokputer_tasks.jsonl", split="train")
  data = data.train_test_split(test_size=0.2)
  tokenizer = AutoTokenizer.from_pretrained("xai-org/grok-1")  # Or Llama proxy
  def tokenize(examples):
      return tokenizer(examples["instruction"], examples["response"], truncation=True, max_length=512)
  tokenized_data = data.map(tokenize, batched=True)
  tokenized_data.save_to_disk("lora_dataset")
  ```  
  Dataset Idea: 1K examples from session logs (e.g., "Decompose task: Scan vault" → subtask JSON).

- **🔴 id: lora-model-load** (Status: pending)  
  Content: Load base model: Use Grok-1 or compatible model (e.g., Llama if Grok not open). Apply LoRA config: rank=16, alpha=32, target_modules=['q_proj', 'v_proj'], lora_dropout=0.05. Use PEFT for efficient loading (4-bit quantization via bitsandbytes).  
  Priority: high  
  Code Snippet:  
  ```python
  from peft import LoraConfig, get_peft_model
  from transformers import AutoModelForCausalLM, BitsAndBytesConfig
  import torch

  bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
  model = AutoModelForCausalLM.from_pretrained("xai-org/grok-1", quantization_config=bnb_config, device_map="auto")
  lora_config = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj", "v_proj"], lora_dropout=0.05, bias="none", task_type="CAUSAL_LM")
  model = get_peft_model(model, lora_config)
  model.print_trainable_parameters()  # ~0.5% trainable
  ```

- **🟡 id: lora-training-script** (Status: pending)  
  Content: Implement training loop: Use HuggingFace Trainer or custom script with SFTTrainer from trl. Set hyperparameters: epochs=3, batch_size=4 (gradient acc=4), lr=1e-4, warmup=0.1. Enable gradient checkpointing, Deepspeed if multi-GPU. Monitor loss/val perplexity.  
  Priority: medium  
  Code Snippet:  
  ```python
  from trl import SFTTrainer
  from transformers import TrainingArguments

  args = TrainingArguments(
      output_dir="lora_grokputer",
      num_train_epochs=3,
      per_device_train_batch_size=4,
      gradient_accumulation_steps=4,
      learning_rate=1e-4,
      warmup_ratio=0.1,
      gradient_checkpointing=True,
      fp16=True,
      logging_steps=10,
      evaluation_strategy="steps",
      save_steps=500,
      load_best_model_at_end=True,
  )
  trainer = SFTTrainer(
      model=model,
      args=args,
      train_dataset=tokenized_data["train"],
      eval_dataset=tokenized_data["test"],
      tokenizer=tokenizer,
      packing=True,
      max_seq_length=512,
  )
  trainer.train()
  trainer.save_model("lora_adapter")
  ```  
  Run: `accelerate launch train_lora.py`.

- **🟡 id: lora-evaluation** (Status: pending)  
  Content: Evaluate model: After training, merge LoRA adapters. Test on held-out data: Compute perplexity, accuracy on tasks (e.g., code generation for agents, task decomposition). Compare to base model. Use ROUGE/BLEU for generation tasks.  
  Priority: medium  
  Code Snippet:  
  ```python
  from peft import PeftModel
  merged_model = PeftModel.from_pretrained(base_model, "lora_adapter")
  merged_model = merged_model.merge_and_unload()
  # Evaluate with transformers' evaluate library
  from evaluate import load
  rouge = load("rouge")
  results = rouge.compute(predictions=generated, references=ground_truth)
  ```

- **🟡 id: lora-integration** (Status: pending)  
  Content: Integrate into Grokputer: Save LoRA weights. Load in GrokClient: Use PEFTModel.from_pretrained with adapter. Update main.py to use fine-tuned model for specific agents (e.g., Coordinator). Test end-to-end swarm performance.  
  Priority: medium  
  Next: Modify `src/grok_client.py` to load adapter conditionally (e.g., `--use-lora` flag).

- **🟢 id: lora-optimization** (Status: pending)  
  Content: Optimize: Prune/quantize LoRA weights if needed. Experiment with ranks (8-64). Add PEFT task-specific adapters (e.g., one for OCR, one for action planning). Track VRAM usage (<8GB target).  
  Priority: low

- **🟢 id: lora-docs-tests** (Status: pending)  
  Content: Documentation and testing: Update README/DEVELOPMENT_PLAN.md with LoRA setup. Write unit tests for loading/training. Add CI script for fine-tuning. Document savings (e.g., 90% fewer params trained).  
  Priority: low

## Next Actions
- Complete `lora-setup-env` (in progress).
- Proceed to data prep once env is ready.
- Monitor: VRAM <8GB, train time <2 hours on single GPU.

ZA GROKA! 🚀 *Generated on 2025-11-08.*