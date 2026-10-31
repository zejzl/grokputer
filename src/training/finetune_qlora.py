"""
QLoRA Fine-Tuning for Grokputer Self-Improvement

Optimized for AMD Radeon RX 7900 XT (20GB VRAM) with ROCm.

This script:
1. Loads failed sessions from logs/ directory
2. Builds corrective training dataset
3. Trains LoRA adapters with 4-bit quantization
4. Saves adapter to lora-adapters/ directory

Author: Claude Code
Date: 2025-11-08
"""

import os
import json
import logging
import torch
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, PeftModel
from trl import SFTConfig, SFTTrainer
from datasets import Dataset

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for QLoRA training."""
    # Paths
    logs_dir: Path = Path("logs")
    output_dir: Path = Path("lora-adapters")

    # Model
    base_model: str = "meta-llama/Llama-2-7b-hf"  # or "mistralai/Mistral-7B-v0.1"

    # LoRA config
    lora_r: int = 16  # Rank (8-64 typical, higher = more capacity)
    lora_alpha: int = 32  # Scaling (usually 2x rank)
    lora_dropout: float = 0.05
    target_modules: List[str] = None  # Will be set in __post_init__

    # Quantization (for AMD ROCm)
    use_4bit: bool = True  # Set to False if bitsandbytes-rocm not available

    # Training hyperparameters
    num_epochs: int = 3
    batch_size: int = 4  # Adjust based on VRAM
    gradient_accumulation_steps: int = 4  # Effective batch = 16
    learning_rate: float = 2e-4
    max_seq_length: int = 2048

    # Dataset
    min_failed_sessions: int = 5  # Minimum failed sessions needed to train
    max_rating_for_failure: int = 3  # Sessions rated ≤3 are "failures"

    def __post_init__(self):
        """Set target modules based on model architecture."""
        if self.target_modules is None:
            # Llama/Mistral attention layers
            self.target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]


def require_gpu():
    """Exit with a hint when no GPU is visible. Called from main(), not at import, so the data and config helpers can be tested without a GPU."""
    if not torch.cuda.is_available():
        print("=" * 70)
        print("[ERROR] GPU not detected!")
        print("   Make sure AMD ROCm is installed:")
        print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.1")
        print("=" * 70)
        raise SystemExit(1)

    print("=" * 70)
    print("Grokputer QLoRA Fine-Tuning (AMD ROCm)")
    print("=" * 70)
    print(f"[OK] PyTorch version: {torch.__version__}")
    print(f"[OK] GPU: {torch.cuda.get_device_name(0)}")
    print(f"[OK] VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print("=" * 70)


FEEDBACK_FILE = "feedback.json"


def record_feedback(session_dir: Path, rating: int, what_went_wrong: List[str], comment: str = "") -> Path:
    """Attach a rating to a finished session. This is the supported way to create training data.

    SessionLogger writes session.json (task, tool_executions, errors) but never asks for a rating, so the rating
    lives in a sidecar file next to it: {"user_rating": 1-5, "what_went_wrong": [...], "feedback_comment": "..."}.
    """
    if not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5:
        raise ValueError("rating must be an integer from 1 to 5")
    if not what_went_wrong or not all(isinstance(i, str) and i.strip() for i in what_went_wrong):
        raise ValueError("what_went_wrong must list at least one issue (non-empty strings)")
    path = Path(session_dir) / FEEDBACK_FILE
    path.write_text(json.dumps({"user_rating": rating, "what_went_wrong": list(what_went_wrong),
                                "feedback_comment": comment}, indent=2), encoding="utf-8")
    return path


def read_session(session_dir: Path) -> Dict[str, Any] | None:
    """One session as {task, rating, issues, comment, actions}, or None when it has no usable data.

    Reads what the current SessionLogger writes (session.json: top-level "task" and "tool_executions", each with
    "tool") plus the feedback.json sidecar. The older layout, with everything under session.json "metadata"
    (user_rating, what_went_wrong, feedback_comment, task) and "iterations[].tool_results[].function_name", still loads.
    """
    session_json = session_dir / "session.json"
    if not session_json.exists():
        return None
    with open(session_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return None

    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    feedback = {}
    feedback_json = session_dir / FEEDBACK_FILE
    if feedback_json.exists():
        with open(feedback_json, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        feedback = loaded if isinstance(loaded, dict) else {}

    def pick(key):
        return feedback.get(key, meta.get(key))

    actions = [e.get("tool", "unknown") for e in data.get("tool_executions", []) if isinstance(e, dict)]
    for iteration in data.get("iterations", []) if isinstance(data.get("iterations"), list) else []:
        for result in iteration.get("tool_results", []):
            actions.append(result.get("function_name", "unknown"))
    return {
        "task": data.get("task") or meta.get("task") or "Unknown task",
        "rating": pick("user_rating"),
        "issues": pick("what_went_wrong") or [],
        "comment": pick("feedback_comment") or "",
        "actions": actions,
    }


def load_failed_sessions(config: TrainingConfig) -> List[Dict[str, Any]]:
    """
    Load sessions rated at or below config.max_rating_for_failure.

    Args:
        config: Training configuration

    Returns:
        List of failed sessions as read_session() dicts
    """
    logger.info(f"Loading sessions from {config.logs_dir}...")

    if not config.logs_dir.exists():
        logger.error(f"Logs directory not found: {config.logs_dir}")
        return []

    failed_sessions = []

    session_dirs = [d for d in config.logs_dir.iterdir()
                   if d.is_dir() and d.name.startswith("session_")]

    logger.info(f"Found {len(session_dirs)} total sessions")

    for session_dir in session_dirs:
        try:
            session = read_session(session_dir)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"  Skipping {session_dir.name}: {e}")
            continue
        if session is None:
            continue

        rating = session["rating"]
        if isinstance(rating, (int, float)) and not isinstance(rating, bool) and rating <= config.max_rating_for_failure:
            failed_sessions.append(session)
            logger.debug(f"  Loaded failed session: {session_dir.name} (rating: {rating})")

    logger.info(f"[OK] Loaded {len(failed_sessions)} failed sessions (rating <= {config.max_rating_for_failure})")

    return failed_sessions


def generate_corrective_examples(sessions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Generate corrective training examples from failed sessions.

    For each failed session, create an example showing:
    - What Grok was asked to do (instruction)
    - What the initial state was (input)
    - What Grok should have done (output - corrected plan)

    Args:
        sessions: List of failed session data

    Returns:
        List of training examples in Alpaca format
    """
    logger.info("Generating corrective examples...")

    examples = []

    for session in sessions:
        task = session.get("task", "Unknown task")
        issues = session.get("issues", [])
        comment = session.get("comment", "")

        # Build corrective instruction
        if not issues:
            continue  # Skip if no specific issues identified

        actions_taken = session.get("actions", [])

        # Generate corrected plan based on issues
        corrections = generate_corrections(task, actions_taken, issues, comment)

        if not corrections:
            continue

        # Create training example in Alpaca format
        example = {
            "instruction": f"Complete this task: {task}",
            "input": f"Previous attempt failed with these issues: {', '.join(issues)}",
            "output": corrections
        }

        examples.append(example)
        logger.debug(f"  Created example for: {task[:50]}...")

    logger.info(f"✓ Generated {len(examples)} corrective examples")

    return examples


def generate_corrections(task: str, actions: List[str], issues: List[str], comment: str) -> str:
    """
    Generate corrected action plan based on failure analysis.

    Uses heuristics to suggest better approaches.

    Args:
        task: Original task description
        actions: List of actions Grok took
        issues: List of issues that occurred
        comment: User's feedback comment

    Returns:
        Corrected plan as string
    """
    corrections = []

    # Heuristic corrections based on common issues
    if "OCR confidence low" in issues or "text recognition failed" in issues:
        corrections.append("1. Capture high-quality screenshot (quality=high, region=specific area)")
        corrections.append("2. Use OCR with minimum confidence threshold of 0.85")
        corrections.append("3. If OCR fails, try alternative methods (keyboard shortcut, menu navigation)")

    if "Wrong action selected" in issues or "incorrect command" in issues:
        corrections.append("4. Validate UI state before taking action")
        corrections.append("5. Use pyautogui.locateOnScreen() for precise element detection")
        corrections.append("6. Double-check coordinates match target element")

    if "Timeout" in issues or "took too long" in issues:
        corrections.append("7. Break task into smaller, independent subtasks")
        corrections.append("8. Add intermediate validation checkpoints")
        corrections.append("9. Set realistic timeouts for each step")

    if "Coordination issue" in issues or "agents confused" in issues:
        corrections.append("10. Clarify agent responsibilities (Observer captures, Actor executes, Validator confirms)")
        corrections.append("11. Use explicit handoff messages with context")
        corrections.append("12. Wait for confirmation before proceeding to next step")

    # Add comment if provided
    if comment:
        corrections.append(f"\nUser feedback: {comment}")
        corrections.append("Consider this feedback when planning actions.")

    # If no specific corrections, provide general advice
    if not corrections:
        corrections.append("1. Review the task requirements carefully")
        corrections.append("2. Break complex tasks into simpler steps")
        corrections.append("3. Validate each step before proceeding")
        corrections.append("4. Use appropriate tools for each subtask")

    return "\n".join(corrections)


def build_dataset(config: TrainingConfig) -> Dataset:
    """
    Build training dataset from failed sessions.

    Args:
        config: Training configuration

    Returns:
        Hugging Face Dataset object

    Raises:
        ValueError: If not enough failed sessions
    """
    # Load failed sessions
    sessions = load_failed_sessions(config)

    if len(sessions) < config.min_failed_sessions:
        raise ValueError(
            f"Not enough failed sessions! Found {len(sessions)}, need at least {config.min_failed_sessions}\n"
            f"Rate finished sessions with record_feedback(session_dir, rating, [issues]) (writes feedback.json next to session.json)."
        )

    # Generate corrective examples
    examples = generate_corrective_examples(sessions)

    if not examples:
        raise ValueError("No training examples generated! Pass at least one issue to record_feedback().")

    # Create Hugging Face Dataset
    dataset = Dataset.from_list(examples)

    logger.info(f"✓ Built dataset with {len(examples)} examples")

    return dataset


def get_next_version(output_dir: Path) -> int:
    """Get next LoRA version number."""
    if not output_dir.exists():
        return 1

    versions = []
    for d in output_dir.iterdir():
        if d.is_dir() and d.name.startswith("lora-v"):
            try:
                version = int(d.name.split("-v")[-1])
                versions.append(version)
            except ValueError:
                continue

    return max(versions) + 1 if versions else 1


def build_sft_config(config: TrainingConfig, output_path: Path) -> SFTConfig:
    """Training arguments for the pinned stack (transformers 4.57, trl 0.25): packing and max_length live in SFTConfig."""
    return SFTConfig(
        output_dir=str(output_path),
        num_train_epochs=config.num_epochs,
        per_device_train_batch_size=config.batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        fp16=torch.cuda.is_available(),  # Mixed precision training; the setting is rejected without a GPU
        bf16=False,  # SFTConfig turns bf16 on by default when fp16 is off, which fails on a machine without a GPU
        logging_steps=10,
        save_steps=100,
        save_total_limit=3,  # Keep only last 3 checkpoints
        eval_strategy="no",  # No eval set for small datasets
        load_best_model_at_end=False,
        report_to="none",  # No W&B/tensorboard
        remove_unused_columns=False,
        packing=True,  # Pack short sequences for efficiency
        max_length=config.max_seq_length,
    )


def train_qlora(config: TrainingConfig, dataset: Dataset):
    """
    Train QLoRA adapter on dataset.

    Args:
        config: Training configuration
        dataset: Training dataset
    """
    logger.info("=" * 70)
    logger.info("STARTING QLORA TRAINING")
    logger.info("=" * 70)

    # 1. Setup quantization config (AMD ROCm compatible)
    if config.use_4bit:
        logger.info("Loading model with 4-bit quantization...")
        try:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,  # Nested quantization
                bnb_4bit_quant_type="nf4",       # Normal Float 4
                bnb_4bit_compute_dtype=torch.bfloat16
            )
        except Exception as e:
            logger.warning(f"4-bit quantization failed: {e}")
            logger.warning("Falling back to fp16 (your 20GB VRAM can handle it!)")
            bnb_config = None
            config.use_4bit = False
    else:
        logger.info("Loading model in fp16 (no quantization)...")
        bnb_config = None

    # 2. Load base model
    logger.info(f"Loading base model: {config.base_model}")
    logger.info("(This may take 5-10 minutes for first download...)")

    try:
        model = AutoModelForCausalLM.from_pretrained(
            config.base_model,
            quantization_config=bnb_config,
            device_map="auto",  # Auto GPU distribution
            trust_remote_code=True,
            torch_dtype=torch.bfloat16 if not config.use_4bit else None
        )
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.error("Common fixes:")
        logger.error("  1. Check model name is correct")
        logger.error("  2. Login to Hugging Face: huggingface-cli login")
        logger.error("  3. For Llama models, request access at meta.com")
        raise

    # 3. Load tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(config.base_model)
    tokenizer.pad_token = tokenizer.eos_token  # Fix padding
    tokenizer.padding_side = "right"

    # 4. Apply LoRA adapters
    logger.info("Applying LoRA adapters...")
    lora_config = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        target_modules=config.target_modules,
        lora_dropout=config.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)
    trainable_params, all_params = model.get_nb_trainable_parameters()
    logger.info(f"✓ Trainable parameters: {trainable_params:,} / {all_params:,} "
                f"({100 * trainable_params / all_params:.2f}%)")

    # 5. Setup training arguments
    version = get_next_version(config.output_dir)
    output_path = config.output_dir / f"lora-v{version}"

    training_args = build_sft_config(config, output_path)

    # 6. Formatting function for Alpaca prompts
    def formatting_func(example):
        """Format example into prompt template."""
        instruction = example.get("instruction", "")
        input_text = example.get("input", "")
        output_text = example.get("output", "")

        if input_text:
            prompt = f"### Instruction: {instruction}\n### Input: {input_text}\n### Response: {output_text}<|endoftext|>"
        else:
            prompt = f"### Instruction: {instruction}\n### Response: {output_text}<|endoftext|>"

        return prompt

    # 7. Create trainer
    logger.info("Creating SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=training_args,
        processing_class=tokenizer,
        formatting_func=formatting_func,
    )

    # 8. Train!
    logger.info("=" * 70)
    logger.info(f"🚀 TRAINING STARTING (LoRA-v{version})")
    logger.info(f"   Epochs: {config.num_epochs}")
    logger.info(f"   Batch size: {config.batch_size} (effective: {config.batch_size * config.gradient_accumulation_steps})")
    logger.info(f"   Learning rate: {config.learning_rate}")
    logger.info(f"   Dataset size: {len(dataset)} examples")
    logger.info(f"   Estimated time: 1-2 hours on RX 7900 XT")
    logger.info("=" * 70)
    logger.info("☕ Grab a coffee! This will take a while...")
    logger.info("=" * 70)

    start_time = datetime.now()

    try:
        trainer.train()
    except Exception as e:
        logger.error(f"Training failed: {e}")
        logger.error("Common fixes:")
        logger.error("  1. Reduce batch_size if OOM (try batch_size=2)")
        logger.error("  2. Reduce lora_r if OOM (try r=8)")
        logger.error("  3. Enable gradient_checkpointing for more VRAM")
        raise

    training_time = (datetime.now() - start_time).total_seconds()

    # 9. Save adapter
    logger.info("=" * 70)
    logger.info("💾 SAVING LORA ADAPTER")
    logger.info("=" * 70)

    trainer.save_model(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    # Save training metadata
    metadata = {
        "version": version,
        "base_model": config.base_model,
        "lora_r": config.lora_r,
        "lora_alpha": config.lora_alpha,
        "dataset_size": len(dataset),
        "training_time_seconds": training_time,
        "training_date": datetime.now().isoformat(),
        "config": {
            "num_epochs": config.num_epochs,
            "batch_size": config.batch_size,
            "learning_rate": config.learning_rate,
            "use_4bit": config.use_4bit
        }
    }

    metadata_path = output_path / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"✓ LoRA adapter saved to: {output_path}")
    logger.info(f"✓ Training time: {training_time / 60:.1f} minutes")
    logger.info("=" * 70)
    logger.info("🎉 TRAINING COMPLETE!")
    logger.info("=" * 70)
    logger.info(f"\nNext steps:")
    logger.info(f"  1. Test the adapter:")
    logger.info(f"     python -c \"from src.grok_client import GrokClient; client = GrokClient(lora_version='lora-v{version}')\"")
    logger.info(f"  2. Run some tasks and compare with base model")
    logger.info(f"  3. If better, update .env: LORA_VERSION=lora-v{version}")
    logger.info(f"\nAdapter location: {output_path}")
    logger.info("=" * 70)

    return version


def main():
    """Main training pipeline."""
    require_gpu()
    # Parse config (could add argparse here)
    config = TrainingConfig()

    print("\n📋 Training Configuration:")
    print(f"  Base model: {config.base_model}")
    print(f"  LoRA rank: {config.lora_r}")
    print(f"  Batch size: {config.batch_size}")
    print(f"  Epochs: {config.num_epochs}")
    print(f"  4-bit quantization: {config.use_4bit}")
    print(f"  Min failed sessions needed: {config.min_failed_sessions}")
    print()

    try:
        # Build dataset
        dataset = build_dataset(config)

        # Train
        version = train_qlora(config, dataset)

        print("\n✅ SUCCESS! Grokputer is now smarter.")
        print(f"   LoRA-v{version} ready for deployment.")
        print("\nZA GROKA - THE ETERNAL HIVE LEARNS! 🤖🧠⚡")

    except ValueError as e:
        logger.error(f"\n❌ {e}")
        logger.info("\nTo collect more training data:")
        logger.info("  1. Run: python main.py --task \"your task here\"")
        logger.info("  2. Rate the task <4 stars if it fails")
        logger.info("  3. Specify what went wrong (OCR, wrong action, timeout, etc.)")
        logger.info(f"  4. Repeat until you have {config.min_failed_sessions}+ failed sessions")
        logger.info("  5. Run this script again!")
        exit(1)
    except Exception as e:
        logger.error(f"\n❌ Training failed: {e}")
        logger.error("Check error messages above for troubleshooting.")
        exit(1)


if __name__ == "__main__":
    main()
