import torch
import json
from datasets import load_from_disk
from transformers import AutoTokenizer, pipeline
from peft import PeftModel
from evaluate import load
from src.lora.load_model import load_lora_model  # Base model loader

def evaluate_lora(adapter_path="./lora_adapter", model_name="meta-llama/Llama-2-7b-hf"):
    """
    Evaluate trained LoRA model:
    - Merge adapter and compute perplexity.
    - Generate responses on eval set for ROUGE/BLEU.
    - Simple accuracy (e.g., valid JSON for tasks).
    - Compare to base model.
    """
    # Load base model and tokenizer
    base_model, tokenizer = load_lora_model(model_name=model_name, use_quantization=True)
    
    # Load and merge LoRA
    lora_model = PeftModel.from_pretrained(base_model, adapter_path)
    merged_model = lora_model.merge_and_unload()
    print(f"Merged LoRA model from {adapter_path}")
    
    # Load eval dataset
    dataset = load_from_disk("lora_dataset")
    eval_dataset = dataset["test"]
    
    # Perplexity calculation
    from torch.utils.data import DataLoader
    def compute_perplexity(model, tokenizer, dataset, batch_size=4):
        model.eval()
        total_loss = 0
        total_tokens = 0
        device = next(model.parameters()).device
        
        dataloader = DataLoader(dataset, batch_size=batch_size, collate_fn=lambda x: tokenizer.pad(x, return_tensors="pt"))
        for batch in dataloader:
            inputs = {k: v.to(device) for k, v in batch.items() if k in ["input_ids", "attention_mask"]}
            with torch.no_grad():
                outputs = model(**inputs, labels=inputs["input_ids"])
                total_loss += outputs.loss.item() * inputs["input_ids"].numel()
                total_tokens += inputs["input_ids"].numel()
        
        perplexity = torch.exp(torch.tensor(total_loss / total_tokens))
        return perplexity.item()
    
    lora_ppl = compute_perplexity(merged_model, tokenizer, eval_dataset)
    base_ppl = compute_perplexity(base_model, tokenizer, eval_dataset)  # Base comparison
    print(f"LoRA Perplexity: {lora_ppl:.4f} (Base: {base_ppl:.4f})")
    
    # Generation and metrics
    generator = pipeline("text-generation", model=merged_model, tokenizer=tokenizer, device=0 if torch.cuda.is_available() else -1)
    base_generator = pipeline("text-generation", model=base_model, tokenizer=tokenizer, device=0 if torch.cuda.is_available() else -1)
    
    predictions_lora = []
    references = []
    predictions_base = []
    
    for example in eval_dataset.select(range(min(50, len(eval_dataset)))):  # Sample 50
        prompt = example["instruction"]
        ref = example["response"]
        
        # Generate with LoRA
        gen_lora = generator(prompt, max_new_tokens=100, do_sample=True, temperature=0.7)[0]["generated_text"]
        pred_lora = gen_lora.split(prompt)[-1].strip()  # Extract generated part
        
        # Generate with base
        gen_base = base_generator(prompt, max_new_tokens=100, do_sample=True, temperature=0.7)[0]["generated_text"]
        pred_base = gen_base.split(prompt)[-1].strip()
        
        predictions_lora.append(pred_lora)
        predictions_base.append(pred_base)
        references.append(ref)
    
    # ROUGE and BLEU
    rouge = load("rouge")
    bleu = load("bleu")
    
    rouge_lora = rouge.compute(predictions=predictions_lora, references=references)
    rouge_base = rouge.compute(predictions=predictions_base, references=references)
    bleu_lora = bleu.compute(predictions=predictions_lora, references=[[ref] for ref in references])
    bleu_base = bleu.compute(predictions=predictions_base, references=[[ref] for ref in references])
    
    print("ROUGE (LoRA):", {k: f"{v:.4f}" for k, v in rouge_lora.items()})
    print("ROUGE (Base):", {k: f"{v:.4f}" for k, v in rouge_base.items()})
    print(f"BLEU (LoRA): {bleu_lora['bleu']:.4f} (Base: {bleu_base['bleu']:.4f})")
    
    # Simple accuracy: % valid JSON in responses (for task decomp)
    def is_valid_json(s):
        try:
            json.loads(s)
            return True
        except:
            return False
    
    acc_lora = sum(is_valid_json(p) for p in predictions_lora) / len(predictions_lora)
    acc_base = sum(is_valid_json(p) for p in predictions_base) / len(predictions_base)
    print(f"JSON Accuracy (LoRA): {acc_lora:.4f} (Base: {acc_base:.4f})")
    
    return {
        "perplexity_lora": lora_ppl,
        "perplexity_base": base_ppl,
        "rouge_lora": rouge_lora,
        "rouge_base": rouge_base,
        "bleu_lora": bleu_lora["bleu"],
        "bleu_base": bleu_base["bleu"],
        "json_acc_lora": acc_lora,
        "json_acc_base": acc_base,
    }

if __name__ == "__main__":
    results = evaluate_lora()
    print("Evaluation Results:", results)