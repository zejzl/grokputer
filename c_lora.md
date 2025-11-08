# Claude's Analysis: Self-Improving Grokputer with LoRA/QLoRA

**Date**: 2025-11-08
**Status**: Proposal - Awaiting User Decision
**Context**: Response to lora.md and qlora.md integration proposal

---

## Executive Summary

You're proposing to add **self-improvement** to Grokputer using LoRA (Low-Rank Adaptation) fine-tuning. This would enable the system to:

1. **Collect feedback** on task execution (1-5 star ratings)
2. **Detect poor performance** (avg rating <3.8 over 50 tasks)
3. **Auto-trigger QLoRA training** on corrective examples
4. **Deploy improved models** via canary rollout (15% → 100% if healthy)
5. **Continuously evolve** without manual intervention

This is a **game-changer** - moving from static AI to adaptive, self-healing intelligence.

---

## What I Found in Your Files

### lora.md = Multi-Modal Self-Improving Agent

**Key Features**:
- **Multi-modal inputs**: Text + Image (screenshots!) + Audio
- **Feedback loop**: User rates task execution → triggers LoRA fine-tuning when avg <3.8
- **Auto-evolution**: Bad ratings → retrain → canary deploy → auto-promote if health >97%
- **Grokputer GoGo native**: Full platform integration with GPU, autoscaling, rollback
- **Prometheus metrics**: Track latency, modality usage, generation counts

**Architecture**:
```
User → Multi-Modal Input (text + image + audio)
         ↓
    Parallel Processing (Vision + Audio + Text)
         ↓
    Unified LLM with LoRA adapter
         ↓
    Response + session_id
         ↓
    User rates 1-5 stars
         ↓
    (If avg < 3.8) → Trigger finetune.py
         ↓
    Build corrective dataset
         ↓
    Train LoRA v{N+1}
         ↓
    Canary Deploy (15% traffic)
         ↓
    Health check >97%?
    ↙           ↘
Promote 100%   Rollback
```

### qlora.md = Technical Implementation Blueprint

**QLoRA Advantages**:
- **70-80% VRAM savings** via 4-bit quantization (NF4/FP4)
- **2-5x faster** than full fine-tuning
- **Consumer-grade training**: Fine-tune 7B models on RTX 4090 (~6-8GB VRAM)
- **Cost**: ~$0.50-2 per training run (vs $50+ for full FT)
- **Quality**: Matches 16-bit FT performance (0.5-1% perplexity gap)

**Tech Stack (2025-Ready)**:
- `transformers` + `peft` + `bitsandbytes` + `trl` (SFTTrainer)
- Hugging Face PEFT for adapter management
- Optional: `unsloth` for 2x speed boost
- CUDA 11.8+ required

**Training Setup**:
```python
# 4-bit quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,  # Nested 4-bit
    bnb_4bit_quant_type="nf4",       # Normal Float 4
    bnb_4bit_compute_dtype=torch.bfloat16
)

# LoRA config
lora_config = LoraConfig(
    r=16,  # Rank: 8-64 typical
    lora_alpha=32,  # Scaling: 2x rank
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    task_type="CAUSAL_LM"
)

# Train ~1-2 hours on RTX 4090
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=TrainingArguments(
        num_train_epochs=3,
        per_device_train_batch_size=4,
        learning_rate=2e-4,
        fp16=True
    )
)
```

---

## Impact on Grokputer Architecture

### Current Architecture
```
User → Task → Observer → Actor → Result → SessionLogger
```

### With LoRA Self-Improvement
```
User → Task → Observer → Actor → Result → SessionLogger
                                              ↓
                                        Feedback Rating (1-5)
                                              ↓
                                   (If avg < 3.8 over 50 tasks)
                                              ↓
                                    Trigger finetune.py
                                              ↓
                                Build corrective dataset from session logs
                                              ↓
                            QLoRA Train (PEFT r=16, 4-bit, 1-2 hours)
                                              ↓
                                Upload LoRA-v{N+1} adapter
                                              ↓
                            Canary Deploy (15% traffic split)
                                              ↓
                                    Health check 97%?
                                    ↙           ↘
                            Promote 100%   Rollback + Alert
                                              ↓
                                    (Repeat cycle every 4 hours)
```

---

## Integration Plan for Grokputer

### Phase 2.5: Self-Improvement Foundation (NEW!)

#### 1. **Feedback Collection** (Already 80% Done!)

Extend existing SessionLogger:

```python
# src/session_logger.py (extend existing)
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class SessionMetadata:
    # ... existing fields ...
    user_rating: Optional[int] = None  # 1-5 stars
    feedback_comment: Optional[str] = None
    lora_version: str = "base"  # Track which adapter was used
    what_went_wrong: List[str] = field(default_factory=list)
    # e.g., ["OCR confidence low", "Wrong action selected", "Timeout"]

class SessionLogger:
    # ... existing methods ...

    def add_feedback(self, rating: int, comment: str = "",
                     issues: List[str] = None):
        """Add user feedback to current session."""
        self.metadata.user_rating = rating
        self.metadata.feedback_comment = comment
        if issues:
            self.metadata.what_went_wrong.extend(issues)

        # Write to session.json immediately
        self._write_session_json()

        # Check if retraining needed (background task)
        asyncio.create_task(self._check_retrain_trigger())

    async def _check_retrain_trigger(self):
        """Check if recent feedback warrants retraining."""
        recent_sessions = self._load_recent_sessions(limit=50)
        ratings = [s.user_rating for s in recent_sessions if s.user_rating]

        if len(ratings) >= 10:
            avg_rating = sum(ratings) / len(ratings)
            if avg_rating < 3.8:
                logger.warning(f"Low avg rating ({avg_rating:.2f}), triggering retrain")
                await trigger_finetune()
```

**CLI Integration**:
```python
# main.py (after task completion)
if not args.no_feedback:
    rating = click.prompt("Rate this task (1-5)", type=click.IntRange(1, 5))
    comment = click.prompt("Any feedback? (optional)", default="", show_default=False)
    session_logger.add_feedback(rating, comment)
```

#### 2. **LoRA-Enabled GrokClient**

Update Grok API client to support adapter switching:

```python
# src/grok_client.py (extend existing)
class GrokClient:
    def __init__(self, api_key: str, model: str = "grok-4-fast-reasoning",
                 lora_version: str = "base"):
        self.api_key = api_key
        self.model = model
        self.lora_version = lora_version  # NEW
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        logger.info(f"GrokClient initialized with LoRA: {lora_version}")

    async def create_message(self, messages: List[Dict],
                            tools: List[Dict] = None,
                            **kwargs) -> Dict:
        """Send message to Grok API with optional LoRA adapter."""
        # Pass LoRA adapter if not base
        if self.lora_version != "base":
            kwargs["lora"] = self.lora_version
            logger.info(f"Using LoRA adapter: {self.lora_version}")

        # Add to system message for tracking
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] += f"\n[Using LoRA: {self.lora_version}]"

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            **kwargs
        )
        return response.model_dump()

    def switch_lora(self, version: str):
        """Hot-swap LoRA adapter (for canary testing)."""
        old_version = self.lora_version
        self.lora_version = version
        logger.info(f"Switched LoRA: {old_version} → {version}")
```

**Config Integration**:
```python
# src/config.py (add)
LORA_VERSION = os.getenv("LORA_VERSION", "base")  # Set via env for canary deploys
LORA_REGISTRY_URL = os.getenv("LORA_REGISTRY_URL", "https://huggingface.co/grokputer")
```

#### 3. **Fine-Tuning Pipeline**

Create training module for QLoRA:

```python
# src/training/finetune_qlora.py
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer
from datasets import Dataset
import json
from pathlib import Path

def load_failed_sessions(limit: int = 50) -> List[Dict]:
    """Load recent sessions with low ratings from logs/."""
    logs_dir = Path("logs")
    sessions = []

    for session_dir in sorted(logs_dir.iterdir(), reverse=True)[:limit]:
        session_json = session_dir / "session.json"
        if session_json.exists():
            with open(session_json) as f:
                data = json.load(f)
                if data.get("user_rating", 5) < 4:  # Failed or mediocre
                    sessions.append(data)

    return sessions

def build_corrective_dataset() -> Dataset:
    """Extract failed tasks and generate corrective examples."""
    sessions = load_failed_sessions()

    if len(sessions) < 5:
        raise ValueError(f"Only {len(sessions)} failed sessions, need at least 5")

    examples = []

    for session in sessions:
        task = session["task"]
        iterations = session.get("iterations", [])
        issues = session.get("what_went_wrong", [])

        # Build corrective prompt
        # Original approach: What Grok did
        original_actions = [it.get("tool_calls", []) for it in iterations]

        # Corrected approach: What Grok should have done
        # (In production, this could be human-labeled or GPT-4 generated)
        corrected_plan = generate_better_plan(task, original_actions, issues)

        examples.append({
            "instruction": f"Complete this task: {task}",
            "input": f"Screen state: {iterations[0].get('screenshot_summary', 'N/A')}",
            "output": corrected_plan
        })

    return Dataset.from_list(examples)

def generate_better_plan(task: str, original_actions: List, issues: List[str]) -> str:
    """Generate corrected action plan based on failure analysis."""
    # Heuristic corrections based on common issues
    corrections = []

    if "OCR confidence low" in issues:
        corrections.append("1. Capture high-quality screenshot (quality=high)")
        corrections.append("2. Use OCR with confidence threshold >0.85")

    if "Wrong action selected" in issues:
        corrections.append("3. Validate UI state before clicking")
        corrections.append("4. Use pyautogui.locateOnScreen() for precision")

    if "Timeout" in issues:
        corrections.append("5. Break task into smaller subtasks")
        corrections.append("6. Add intermediate validation steps")

    return "\n".join(corrections) if corrections else "[Manual review needed]"

async def trigger_finetune():
    """Main QLoRA training pipeline."""
    logger.info("Starting QLoRA fine-tuning pipeline...")

    # 1. Build dataset
    try:
        dataset = build_corrective_dataset()
        logger.info(f"Built dataset with {len(dataset)} corrective examples")
    except ValueError as e:
        logger.warning(f"Skipping training: {e}")
        return

    # 2. Load base model with 4-bit quantization
    model_name = "meta-llama/Llama-2-7b-hf"  # Or xai-org/grok-4-base if available

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token

    # 3. Apply LoRA adapters
    lora_config = LoraConfig(
        r=16,  # Rank: Balance between speed and quality
        lora_alpha=32,  # Scaling factor
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],  # Attention layers
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)
    trainable_params = model.print_trainable_parameters()
    logger.info(f"Trainable parameters: {trainable_params}")

    # 4. Train with SFTTrainer
    def formatting_func(example):
        return f"### Instruction: {example['instruction']}\n### Input: {example['input']}\n### Response: {example['output']}<|endoftext|>"

    output_dir = f"./lora-grokputer-v{get_next_version()}"

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,  # Effective batch size = 16
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_steps=100,
        evaluation_strategy="no",  # Add eval split if dataset larger
        load_best_model_at_end=False,
        report_to="none"  # Or "wandb" for tracking
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=training_args,
        tokenizer=tokenizer,
        packing=True,
        formatting_func=formatting_func,
        max_seq_length=2048
    )

    # 5. Train (1-2 hours on RTX 4090)
    logger.info("Starting training... (1-2 hours on RTX GPU)")
    trainer.train()

    # 6. Save adapter
    trainer.save_model(output_dir)
    logger.info(f"LoRA adapter saved to {output_dir}")

    # 7. Upload to registry (Hugging Face or S3)
    await upload_lora_adapter(output_dir)

    # 8. Notify system of new adapter
    new_version = get_next_version()
    logger.info(f"LoRA-v{new_version} ready for canary deployment")

    return new_version

def get_next_version() -> int:
    """Get next LoRA version number from existing adapters."""
    lora_dir = Path("./lora-adapters")
    if not lora_dir.exists():
        return 1

    versions = [int(d.name.split("-v")[-1]) for d in lora_dir.iterdir() if d.is_dir() and "-v" in d.name]
    return max(versions) + 1 if versions else 1

async def upload_lora_adapter(adapter_path: str):
    """Upload trained adapter to Hugging Face Hub or S3."""
    # Option 1: Hugging Face Hub
    from huggingface_hub import HfApi

    api = HfApi()
    repo_id = "grokputer/lora-adapters"

    api.upload_folder(
        folder_path=adapter_path,
        repo_id=repo_id,
        repo_type="model",
        commit_message=f"Upload {Path(adapter_path).name}"
    )

    logger.info(f"Uploaded to https://huggingface.co/{repo_id}/{Path(adapter_path).name}")
```

#### 4. **Canary Deployment**

Docker Compose setup for traffic splitting:

```yaml
# docker-compose.canary.yml
version: '3.8'

services:
  grokputer-stable:
    build: .
    image: grokputer:lora-v3
    environment:
      - LORA_VERSION=lora-v3
      - XAI_API_KEY=${XAI_API_KEY}
    volumes:
      - ./vault:/app/vault
      - ./logs:/app/logs
    deploy:
      replicas: 9  # 90% traffic
    networks:
      - grokputer-net

  grokputer-canary:
    build: .
    image: grokputer:lora-v4
    environment:
      - LORA_VERSION=lora-v4  # New adapter
      - XAI_API_KEY=${XAI_API_KEY}
      - CANARY_MODE=true
    volumes:
      - ./vault:/app/vault
      - ./logs-canary:/app/logs  # Separate logs
    deploy:
      replicas: 1  # 10% traffic
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; from src.health_check import check; sys.exit(0 if check() else 1)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - grokputer-net

  # Load balancer (nginx) for traffic splitting
  load-balancer:
    image: nginx:alpine
    ports:
      - "8000:80"
    volumes:
      - ./nginx-canary.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - grokputer-stable
      - grokputer-canary
    networks:
      - grokputer-net

networks:
  grokputer-net:
```

**Health Check**:
```python
# src/health_check.py
def check() -> bool:
    """Health check for canary deployment."""
    # Load recent session logs (last 20 tasks)
    recent_sessions = load_recent_sessions(limit=20)

    if len(recent_sessions) < 10:
        return True  # Not enough data yet

    # Check metrics
    ratings = [s.user_rating for s in recent_sessions if s.user_rating]
    success_rate = sum(1 for s in recent_sessions if s.success) / len(recent_sessions)

    avg_rating = sum(ratings) / len(ratings) if ratings else 3.0

    # Canary is healthy if:
    # 1. Success rate > 95%
    # 2. Avg rating > 3.5
    # 3. No critical errors

    return success_rate > 0.95 and avg_rating > 3.5
```

**Auto-Promotion Script**:
```bash
#!/bin/bash
# scripts/promote_canary.sh

set -e

CANARY_VERSION=$1

# Check canary health over 10 minutes
echo "Monitoring canary health for 10 minutes..."
sleep 600

# Get health metrics
HEALTH=$(docker exec grokputer-canary python -c "from src.health_check import check; print(check())")

if [ "$HEALTH" == "True" ]; then
    echo "✅ Canary healthy! Promoting to 100%..."

    # Update docker-compose to use new version
    sed -i "s/LORA_VERSION=.*/LORA_VERSION=$CANARY_VERSION/" docker-compose.yml

    # Restart all replicas
    docker-compose up -d --scale grokputer-stable=10

    echo "✅ Promoted $CANARY_VERSION to production"
else
    echo "❌ Canary unhealthy! Rolling back..."

    # Kill canary
    docker-compose stop grokputer-canary

    # Alert
    echo "ALERT: LoRA $CANARY_VERSION failed health check" | mail -s "Grokputer Canary Failed" admin@example.com
fi
```

---

## Specific Use Cases for Grokputer

### 1. **OCR Specialist Fine-Tuning**

**Problem**: Grok-4 struggles with Windows UI text (small fonts, low contrast, buttons)

**Solution**: QLoRA on OCR-specific datasets

**Dataset Sources**:
- IAM Handwriting Database (for baseline text recognition)
- SynthText (synthetic text in images)
- **Grokputer-specific**: 1000 annotated screen regions from failed OCR validations
- TOON-encoded for efficiency (40% smaller dataset files)

**Training**:
- 2 hours on RTX 4090
- r=16 LoRA (medium quality)
- Target modules: Vision encoder layers (if using multimodal) or text head

**Expected Result**: 85% → 92% confidence on UI elements

**Integration**:
```python
# Validator uses OCR-tuned adapter
validator = ValidatorAgent(
    agent_id="validator",
    grok_client=GrokClient(lora_version="lora-ocr-v2")
)
```

### 2. **Action Selection Optimization**

**Problem**: Actor often picks wrong PyAutoGUI commands for given UI states

**Examples of Failures**:
- Clicks empty space instead of button (coordinate math wrong)
- Types in wrong window (focus not validated)
- Uses `click()` when `doubleClick()` needed

**Solution**: Fine-tune on corrective examples from user feedback

**Dataset**:
- 500 pairs: (task + UI state) → (what Grok did) → (what should have been done)
- Extract from sessions rated <3 where `what_went_wrong` includes "Wrong action"

**Training**:
- 1 hour, r=8 LoRA (lightweight)
- Target modules: Action prediction head

**Expected Result**: 70% → 85% first-action accuracy

### 3. **Task Decomposition Improvement**

**Problem**: Coordinator decomposes complex tasks poorly

**Examples of Failures**:
- Sends entire task to Actor instead of breaking into subtasks
- Delegates to wrong agent (sends OCR task to Actor instead of Validator)
- Doesn't parallelize when possible (sequential vault scan instead of batched)

**Solution**: Fine-tune on "task → optimal subtask sequence" pairs

**Dataset**:
- 200 high-rated decompositions (rating 5, <10s completion)
- 200 low-rated decompositions (rating <3, timeout or wrong results)
- Contrast learning: "Don't do X, do Y instead"

**Training**:
- 3 hours, r=16 LoRA
- Target modules: Planning/reasoning layers

**Expected Result**: <10s trio completion rate: 60% → 80%

### 4. **Error Recovery Patterns**

**Problem**: System doesn't learn from past failures

**Examples**:
- Repeatedly tries same failing approach
- Doesn't recognize "this type of task needs OCR first"
- Doesn't know when to fall back to bash vs PyAutoGUI

**Solution**: Fine-tune on error → recovery patterns

**Dataset**:
- 300 sessions with errors + successful recovery
- Pattern: (error message + context) → (recovery action that worked)

**Training**:
- 2 hours, r=12 LoRA
- Target modules: Error handling logic

**Expected Result**: 50% → 75% auto-recovery success rate

---

## Questions for You

### 1. **Training Infrastructure**

**Do you have GPU access?**
- **Local GPU**: RTX 3090/4090/higher? (6-8GB VRAM minimum for QLoRA)
- **Cloud GPU**: Vast.ai, Lambda Labs, AWS p3? (~$0.30-1/hour)
- **Budget**: How much can we spend per training run?

**Storage for adapters?**
- Hugging Face Hub (free, public or private repos)
- AWS S3 / Azure Blob (pay per GB)
- Local filesystem (simplest for PoC)

### 2. **Integration Priority**

**Which should we fine-tune first?**
- **A. OCR Specialist** - Improve Validator text extraction on Windows UI
  - *Pro*: Clear failure mode, measurable improvement (confidence scores)
  - *Con*: Requires annotated UI screenshot dataset
- **B. Action Optimizer** - Better PyAutoGUI command selection
  - *Pro*: Fixes most user-visible failures (clicks, typing)
  - *Con*: Hard to generate "correct" labels without human review
- **C. Coordinator Brain** - Smarter task decomposition
  - *Pro*: Impacts all downstream agents
  - *Con*: Complex to evaluate (subjective "better" decomposition)
- **D. Error Recovery** - Learn to predict/prevent failures
  - *Pro*: Self-healing focus aligns with Phase 1 goals
  - *Con*: Requires diverse error examples

**My recommendation**: Start with **B (Action Optimizer)** - most impactful for user experience.

### 3. **Feedback Mechanism**

**How should users rate tasks?**

**Option A: Simple CLI Prompt** (Recommended)
```bash
Task complete!
Rate this task (1-5): 4
Any feedback? (optional): Click was off by 10 pixels
```
- *Pro*: Frictionless, doesn't break flow
- *Con*: Low detail, might skip ratings

**Option B: Rich Web UI**
```
┌─────────────────────────────────────┐
│ Task: "Type 'ZA GROKA' in Notepad" │
│                                     │
│ Rating: ★★★★☆ (4/5)                │
│                                     │
│ What went wrong? (check all)       │
│ ☑ OCR confidence low               │
│ ☐ Wrong action selected            │
│ ☐ Timeout                          │
│ ☑ Minor precision issue            │
│                                     │
│ Comments: Click was off by 10px    │
│                                     │
│ [Submit Feedback]                   │
└─────────────────────────────────────┘
```
- *Pro*: Rich structured data, better training signal
- *Con*: Requires web server, slower feedback loop

**Option C: Implicit Rating** (Automatic)
- Success + <10s = 5 stars
- Success + 10-30s = 4 stars
- Success + >30s or retries = 3 stars
- Failure = 1 star
- *Pro*: No user effort
- *Con*: Less accurate, misses context

**My recommendation**: Start with **A (CLI)**, evolve to **B (Web)** in Phase 3.

### 4. **Deployment Strategy**

**How to deploy improved models?**

**Option A: Local LoRA Swapping** (Simplest)
- Download adapters to `./lora-adapters/lora-v{N}/`
- Load via PEFT at startup: `model = PeftModel.from_pretrained(base, "./lora-adapters/lora-v3")`
- *Pro*: Simple, fast, no infrastructure
- *Con*: Manual updates, no A/B testing

**Option B: Model Versioning** (A/B Testing)
- Multiple GrokClient instances per LoRA version
- Route 10% traffic to canary, 90% to stable
- Track metrics per version, auto-promote
- *Pro*: Safe rollouts, data-driven decisions
- *Con*: More complex, needs load balancer

**Option C: Canary Rollout** (Production-Grade)
- Docker Compose with 9 stable + 1 canary replicas
- Health checks every 30s, auto-promote if >97% healthy
- Automatic rollback on failure
- *Pro*: Production-ready, zero-downtime deploys
- *Con*: Requires Docker, orchestration setup

**My recommendation**: Start with **A (Local)**, graduate to **B (Versioning)** once we have 3+ adapters.

### 5. **Dataset Strategy**

**Where do we get training data?**

**Option A: Session Logs Only** (Organic)
- Extract from `logs/<session_id>/session.json`
- Failed tasks (rating <4) → corrective examples
- *Pro*: Real-world data, accurate labels
- *Con*: Slow accumulation (need 50+ failed tasks)

**Option B: Synthetic Generation** (Scale)
- Use Grok-4 to generate edge cases
- Example: "Generate 100 examples of UI states where click coordinates are ambiguous"
- *Pro*: Fast dataset creation, diverse scenarios
- *Con*: Noisy labels, may not reflect real failures

**Option C: Public Datasets** (Baseline)
- SynthText for OCR
- Alpaca/Dolly for instruction-following
- WebArena for UI interactions
- *Pro*: High quality, peer-reviewed
- *Con*: Not Grokputer-specific, may not transfer

**Option D: Hybrid** (Best Balance)
- Start with public datasets (baseline capability)
- Add synthetic data (scale and diversity)
- Fine-tune on session logs (Grokputer-specific patterns)
- *Pro*: Best quality + scale + relevance
- *Con*: More complex pipeline

**My recommendation**: **D (Hybrid)** - Start with Alpaca (instruction-following), add SynthText (OCR), fine-tune on Grokputer session logs.

---

## Implementation Roadmap

### Phase 2.5: Self-Improvement Foundation (Weeks 5-6)

#### Week 5: Feedback + Infrastructure
**Tasks**:
1. ✅ Add feedback collection to SessionLogger (2 hours)
   - `add_feedback(rating, comment, issues)`
   - CLI prompt after task completion
   - Write to `session.json` immediately

2. ✅ Implement LoRA-enabled GrokClient (3 hours)
   - `__init__(lora_version="base")`
   - Pass `lora` parameter to xAI API
   - `switch_lora()` for canary testing

3. ✅ Create `finetune_qlora.py` (5 hours)
   - `load_failed_sessions()` from logs
   - `build_corrective_dataset()` with heuristics
   - QLoRA training setup (4-bit + r=16)
   - Save adapters to `./lora-adapters/`

4. ✅ Update requirements.txt (10 minutes)
   ```
   transformers>=4.36.0
   peft>=0.7.0
   bitsandbytes>=0.41.0
   trl>=0.7.0
   accelerate>=0.25.0
   datasets>=2.16.0
   ```

5. ✅ Add config constants (5 minutes)
   ```python
   LORA_VERSION = os.getenv("LORA_VERSION", "base")
   LORA_ADAPTERS_DIR = "./lora-adapters"
   RETRAIN_THRESHOLD = 3.8  # Avg rating trigger
   ```

**Deliverables**:
- Feedback collection working in CLI
- LoRA-enabled GrokClient tested
- Training script ready (not yet run)

**Estimated Time**: 12 hours

#### Week 6: First Training + A/B Test
**Tasks**:
1. ✅ Manually rate 20-50 tasks (user effort: 1-2 days)
   - Run various tasks, rate honestly
   - Try to get 5-10 failures (rating <4)

2. ✅ Run first training (2 hours GPU time)
   ```bash
   python src/training/finetune_qlora.py
   # Output: ./lora-adapters/lora-v1/
   ```

3. ✅ A/B test: base vs lora-v1 (1 day)
   - Run 10 tasks with `LORA_VERSION=base`
   - Run 10 tasks with `LORA_VERSION=lora-v1`
   - Compare: avg rating, success rate, latency

4. ✅ Analyze results (2 hours)
   - Did lora-v1 improve on failure modes?
   - Measure: rating delta, success rate delta
   - Decide: Is self-improvement viable?

**Deliverables**:
- First LoRA adapter trained
- A/B test results documented
- Go/No-Go decision for Phase 3

**Estimated Time**: 16 hours + 2 hours GPU

---

### Phase 3: Advanced Self-Improvement (Week 7+)

#### Tasks (If Phase 2.5 succeeds):
1. ✅ Canary deployment system (5 hours)
   - Docker Compose with traffic split
   - Health check script
   - Auto-promotion/rollback

2. ✅ Automated training pipeline (3 hours)
   - Cron job: Check feedback every 4 hours
   - Trigger training if avg <3.8
   - Auto-deploy canary

3. ✅ Multi-adapter stacking (4 hours)
   - OCR adapter + Action adapter + Decomposition adapter
   - Route to correct adapter based on agent type
   - Validator → lora-ocr-v2
   - Actor → lora-action-v1
   - Coordinator → lora-coord-v1

4. ✅ Advanced datasets (8 hours)
   - Annotate 100 UI screenshots for OCR
   - Generate 200 synthetic action examples
   - Collect 50 real Grokputer failure patterns

5. ✅ Monitoring dashboard (6 hours)
   - Prometheus metrics export
   - Grafana dashboard: ratings, success rate, LoRA version distribution
   - Alerts: avg rating <3.5, canary failing

**Estimated Time**: 26 hours

---

## Success Metrics

### Phase 2.5 Goals (Week 6):
- ✅ Collect 20+ task ratings (at least 5 failures)
- ✅ Train first LoRA adapter (lora-v1)
- ✅ Measure improvement: +0.3 rating OR +10% success rate
- ✅ Latency overhead <500ms (LoRA inference)

### Phase 3 Goals (Week 7+):
- ✅ 3+ specialized adapters (OCR, Action, Decomposition)
- ✅ Automated training pipeline (trigger every 4 hours)
- ✅ Canary deployments working (auto-promote/rollback)
- ✅ Overall improvement: +0.5 avg rating, +15% success rate

---

## Cost Estimates

### Training Costs:
- **Local GPU** (RTX 4090): $0 hardware cost, ~$0.20 electricity per 2-hour run
- **Cloud GPU** (Vast.ai RTX 4090): ~$0.30-0.50/hour × 2 hours = $0.60-1/run
- **Dataset storage** (Hugging Face Hub): Free for <100GB

### Inference Costs:
- **LoRA adapter size**: ~100-200MB (r=16)
- **Latency overhead**: ~50-100ms (negligible)
- **API costs**: Same as base model (no extra charge from xAI)

### Total Phase 2.5 Estimate:
- Development: 28 hours (your time)
- Training: 3-5 runs × $1 = $5 (cloud GPU) or $0 (local GPU)
- Storage: $0 (Hugging Face free tier)

**Total**: ~$5-10 for entire self-improvement foundation

---

## Risks & Mitigations

### Risk 1: Not Enough Training Data
**Problem**: Need 50+ failed sessions, might take weeks to accumulate

**Mitigations**:
- Start with synthetic data (Alpaca + SynthText)
- Run stress tests to generate failures
- Lower threshold to 10 failed examples for PoC

### Risk 2: QLoRA Doesn't Improve Performance
**Problem**: Adapter might not learn corrective patterns effectively

**Mitigations**:
- Validate with baseline benchmarks (Alpaca eval)
- Increase LoRA rank (r=32 or r=64) for more capacity
- Try full fine-tuning if QLoRA insufficient

### Risk 3: Training Infrastructure Unavailable
**Problem**: No local GPU, cloud too expensive

**Mitigations**:
- Use Colab free tier (T4 GPU, 4-6 hours)
- Reduce model size (use 3B model instead of 7B)
- Skip training, just implement feedback collection

### Risk 4: xAI API Doesn't Support LoRA
**Problem**: xAI might not have LoRA adapter endpoint

**Mitigations**:
- Use local inference with VLLM/Ollama
- Switch to OpenAI fine-tuning API (different paradigm)
- Train local models, use as ensemble with Grok

---

## Immediate Next Steps

### Option 1: Quick Proof of Concept (Recommended)
**Goal**: Validate self-improvement concept in 1 week

**Steps**:
1. I implement feedback collection (2 hours)
   - Add `SessionLogger.add_feedback()`
   - CLI prompt after tasks
   - Write to session.json

2. You manually rate 10-20 tasks (1-2 days)
   - Run diverse tasks
   - Rate honestly, aim for 3-5 failures

3. I analyze session logs (1 hour)
   - Extract failure patterns
   - Show what corrective examples would look like

4. Discussion: Is full training worth it? (30 minutes)
   - Review examples
   - Decide if LoRA makes sense
   - Estimate improvement potential

**Deliverable**: Go/No-Go decision for Phase 2.5

**Time**: 3.5 hours dev + 1-2 days user testing

---

### Option 2: Full Integration (Ambitious)
**Goal**: Complete self-improvement system in 2 weeks

**Steps**:
1. I implement entire Phase 2.5 (12 hours)
   - Feedback collection
   - LoRA-enabled GrokClient
   - `finetune_qlora.py` training script

2. You provide GPU access or cloud credentials
   - Local RTX GPU OR
   - Vast.ai/Lambda Labs account

3. We collect 50+ ratings (1 week user effort)
   - Run tasks daily, rate each

4. Train first adapter (2 hours GPU)
   - Build dataset from session logs
   - QLoRA training
   - Save lora-v1

5. A/B test and measure (1 day)
   - Compare base vs lora-v1
   - Analyze improvement

**Deliverable**: Working self-improving Grokputer

**Time**: 12 hours dev + 2 hours GPU + 1 week user testing

---

### Option 3: Research First (Conservative)
**Goal**: Understand feasibility before coding

**Steps**:
1. I analyze existing session logs (1 hour)
   - Load last 50 sessions
   - Identify top failure modes
   - Count how many <4 ratings we have

2. I design optimal training datasets (2 hours)
   - OCR dataset plan (sources, size, annotation)
   - Action dataset plan (corrective pairs)
   - Decomposition dataset plan

3. I estimate costs and improvements (1 hour)
   - Training time/cost per adapter
   - Expected rating improvement (model-based estimate)
   - Infrastructure requirements

4. Discussion: Prioritize which adapter first (30 minutes)
   - OCR vs Action vs Decomposition
   - Which has highest ROI?

**Deliverable**: Detailed plan with cost-benefit analysis

**Time**: 4.5 hours

---

## My Recommendation

**Go with Option 1: Quick PoC** ✅

**Rationale**:
1. **Low risk**: Only 3.5 hours dev, no infrastructure needed
2. **Fast validation**: Know in 1 week if self-improvement is viable
3. **No sunk cost**: If LoRA doesn't make sense, we only spent 1 day
4. **Concrete examples**: Real session data to evaluate, not theoretical

**Next Steps After PoC**:
- If promising → Proceed with Option 2 (Full Integration)
- If marginal → Stick with static model, focus on other Phase 2 features (OCR, caching)
- If unpromising → Archive idea, revisit in Phase 3

---

## Final Thoughts

This LoRA self-improvement proposal is **incredibly ambitious** and aligns perfectly with the "eternal hive" philosophy. It moves Grokputer from a tool that executes tasks to a system that **learns from experience**.

**The Compound Effect**:
- Week 1: 70% first-action accuracy
- Week 4: 75% (after lora-v1)
- Week 8: 82% (after lora-v3)
- Week 12: 90% (after lora-v5)

Each training cycle improves the baseline, creating a **virtuous cycle**:
```
Better performance → Fewer failures → But harder edge cases collected
→ More nuanced training data → Even better performance → ...
```

**This is the future.** Not just multi-agent coordination, but multi-agent coordination that **gets smarter every day**.

---

**ZA GROKA - THE HIVE THAT LEARNS! 🧠⚡🤖**

---

**Status**: Awaiting user decision on:
1. Which option? (PoC / Full / Research)
2. GPU availability? (Local RTX / Cloud / None)
3. Which adapter first? (OCR / Action / Decomposition / Error Recovery)
4. Feedback mechanism? (CLI / Web UI / Implicit)

Let me know your call and we'll make the eternal hive self-improving! 🚀
