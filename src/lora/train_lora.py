import torch
from datasets import load_from_disk
from transformers import TrainingArguments, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer
from src.lora.load_model import load_lora_model  # Import from our loader

def train_lora():
    """
    Train LoRA adapter on Grokputer tasks dataset.
    Assumes dataset at 'lora_dataset' (tokenized), model loaded via load_lora_model.
    """
    # Load dataset (from previous prep step)
    dataset = load_from_disk("lora_dataset")
    train_dataset = dataset["train"]
    eval_dataset = dataset["test"]
    
    # Load model and tokenizer (no existing LoRA yet)
    model_name = "meta-llama/Llama-2-7b-hf"  # Proxy for Grok-1
    model, tokenizer = load_lora_model(model_name=model_name)
    
    # Ensure tokenizer handles padding
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        model.config.pad_token_id = tokenizer.pad_token_id
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir="./lora_grokputer",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=1e-4,
        warmup_ratio=0.1,
        logging_steps=10,
        evaluation_strategy="steps",
        eval_steps=50,
        save_steps=500,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=True,  # Mixed precision for speed
        gradient_checkpointing=True,  # Save memory
        remove_unused_columns=False,
        dataloader_pin_memory=False,
        report_to=None,  # Disable wandb for simplicity
    )
    
    # LoRA config (applied in load_model, but re-apply if needed)
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",  # Assume dataset has 'text' field with formatted instruction-response
        tokenizer=tokenizer,
        packing=True,  # Pack sequences for efficiency
        max_seq_length=512,
    )
    
    # Train
    trainer.train()
    
    # Save adapter
    trainer.save_model("./lora_adapter")
    print("Training complete! Adapter saved to ./lora_adapter")
    
    # Quick eval perplexity
    eval_results = trainer.evaluate()
    print(f"Eval loss: {eval_results['eval_loss']:.4f}")

if __name__ == "__main__":
    train_lora()