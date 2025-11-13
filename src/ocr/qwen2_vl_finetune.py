"""
Qwen2-VL Fine-tuning for OCR Enhancement

This script fine-tunes Qwen2-VL model for improved OCR performance on images and code screenshots.
"""

import os
import torch
from torch.utils.data import Dataset
from PIL import Image
import json
from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model
import argparse
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCRDataset(Dataset):
    """Dataset for OCR fine-tuning with Qwen2-VL."""

    def __init__(self, data_path: str, processor: AutoProcessor, max_length: int = 512):
        self.data = self.load_data(data_path)
        self.processor = processor
        self.max_length = max_length

    def load_data(self, data_path: str) -> List[Dict[str, Any]]:
        """Load OCR training data."""
        if os.path.isdir(data_path):
            # Directory with image-text pairs
            data = []
            for filename in os.listdir(data_path):
                if filename.endswith(".json"):
                    with open(os.path.join(data_path, filename), "r") as f:
                        item = json.load(f)
                        data.append(item)
        else:
            # Single JSON file
            with open(data_path, "r") as f:
                data = json.load(f)

        logger.info(f"Loaded {len(data)} training samples")
        return data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        image_path = item["image_path"]
        text = item["text"]

        # Load and process image
        image = Image.open(image_path).convert("RGB")

        # Prepare conversation format for Qwen2-VL
        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": "Extract all text from this image accurately:"},
                ],
            },
            {"role": "assistant", "content": text},
        ]

        # Process with tokenizer
        inputs = self.processor.apply_chat_template(conversation, tokenize=True, return_dict=True, return_tensors="pt")

        # Remove batch dimension
        inputs = {k: v.squeeze(0) for k, v in inputs.items()}

        return inputs


def create_sample_dataset(output_dir: str = "ocr_training_data"):
    """Create a sample OCR dataset for demonstration."""
    os.makedirs(output_dir, exist_ok=True)

    # Sample data - in practice, use real OCR datasets
    sample_data = [
        {
            "image_path": "sample_code.png",  # Would need actual image
            "text": "def hello_world():\n    print('Hello, World!')\n    return True",
        },
        {
            "image_path": "sample_text.png",  # Would need actual image
            "text": "This is a sample document with various text content for OCR training.",
        },
    ]

    with open(os.path.join(output_dir, "train.json"), "w") as f:
        json.dump(sample_data, f, indent=2)

    logger.info(f"Created sample dataset in {output_dir}")
    return os.path.join(output_dir, "train.json")


def setup_model_and_tokenizer(model_name: str = "Qwen/Qwen2-VL-2B-Instruct"):
    """Setup Qwen2-VL model and processor."""
    logger.info(f"Loading model: {model_name}")

    # Load model and processor
    model = Qwen2VLForConditionalGeneration.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")

    processor = AutoProcessor.from_pretrained(model_name)

    # Setup LoRA for efficient fine-tuning
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model, processor


def train_ocr_model(
    data_path: str,
    output_dir: str = "./qwen2_vl_ocr_finetuned",
    num_epochs: int = 3,
    batch_size: int = 2,
    learning_rate: float = 2e-5,
):
    """Fine-tune Qwen2-VL for OCR tasks."""

    # Setup model
    model, processor = setup_model_and_tokenizer()

    # Create dataset
    train_dataset = OCRDataset(data_path, processor)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        optim="adamw_torch",
        save_steps=100,
        logging_steps=10,
        learning_rate=learning_rate,
        fp16=True,
        remove_unused_columns=False,
        dataloader_pin_memory=False,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        greater_is_better=False,
    )

    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
    )

    # Start training
    logger.info("Starting OCR fine-tuning...")
    trainer.train()

    # Save the fine-tuned model
    trainer.save_model(output_dir)
    processor.save_pretrained(output_dir)

    logger.info(f"Fine-tuned model saved to {output_dir}")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Qwen2-VL for OCR")
    parser.add_argument("--data_path", type=str, help="Path to training data (JSON file or directory)")
    parser.add_argument("--output_dir", type=str, default="./qwen2_vl_ocr_finetuned", help="Output directory")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=2, help="Batch size")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--create_sample", action="store_true", help="Create sample dataset")

    args = parser.parse_args()

    if args.create_sample:
        args.data_path = create_sample_dataset()

    if not args.data_path:
        logger.error("Please provide --data_path or use --create_sample")
        return

    train_ocr_model(
        data_path=args.data_path,
        output_dir=args.output_dir,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )


if __name__ == "__main__":
    main()
