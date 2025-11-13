# LLM Training Methods Summary

## AsyncThink Protocol
Microsoft Research's framework for "agentic organization" in LLMs, modeling reasoning as dynamic multi-agent collaboration. An organizer LLM delegates subtasks to concurrent worker agents via XML tags (Fork-i, Join-i), forming a DAG of thinking trajectories. Achieves 28% latency reduction and better accuracy on math/reasoning tasks through adaptive parallelism. Learned via SFT + RL (GRPO), generalizes to unseen problems like Sudoku.

## GRPO (Group Relative Policy Optimization)
RL algorithm for multi-agent LLM systems, extending PPO without a critic. Computes shared advantages across episode tokens (organizer + workers), masking exogenous inputs. Reduces variance in sparse-reward settings, enabling stable learning of organizational policies. Used in AsyncThink for 10-15% efficiency gains over PPO.

## PPO Variants in LLMs
Proximal Policy Optimization adaptations for RLHF alignment:
- **PPO-Clip/Penalty**: Clips probability ratios and adds KL penalties for stability.
- **PPO-max**: Combines tricks (reward norm, pretraining) for long-run stability.
- **Adaptive KL PPO**: Dynamically tunes KL for exploration/exploitation balance.
- **Entropy Bonus PPO**: Encourages diverse outputs.
- **Truncated PPO**: Uses partial rollouts for faster alignment.
- **Self-Rewarding PPO**: Uses policy ratios as rewards, needs no RM.
- **Generalized RLPO**: Lagrangian KL penalties, no critic needed.

## DPO (Direct Preference Optimization)
Simplifies RLHF by directly optimizing on preference pairs without RM or RL. Reparameterizes rewards via policy ratios, using sigmoid loss. Matches PPO performance with 1-2 GPU-days vs. 5-10+, highly stable and data-efficient. Powers models like Zephyr.

## KTO (Kahneman-Tversky Optimization)
Aligns LLMs using prospect theory: asymmetric utility for gains/losses on binary desirability signals. No preference pairs needed; maximizes utility with steeper loss penalties. 2-5x less data than DPO, excels in sparse feedback scenarios.

## Mo-KTO (Multi-Objective KTO)
Extends KTO for multiple objectives (e.g., helpfulness + safety) using vector signals and implicit weighting. Achieves Pareto-optimal alignment without RL, cutting compute by 50% vs. MO-RLHF. Handles conflicting preferences via prospect theory aggregation.

These methods evolve LLM training from sequential thinking to organized, aligned intelligence, emphasizing efficiency, stability, and multi-objective balance.

## Local Implementation Feasibility in Grokputer

### 1. **AsyncThink-Inspired Multi-Agent Reasoning**
- **Adaptable**: Enhance Coordinator with dynamic subtask delegation using XML tags for "Fork-i" and "Join-i" patterns.
- **Needed**:
  - Modify `src/agents/coordinator.py` to use tagged prompts
  - Add worker agent pool (already have actors/validators)
  - Test with Grok API for decomposition

### 2. **DPO/KTO for Fine-Tuning**
- **Feasible locally**: Fine-tune a local model (e.g., Qwen-3-4B) on preference data.
- **Needed**:
  - Local model weights (download Qwen-3-4B)
  - Preference dataset (chosen/rejected pairs)
  - TRL library: `pip install trl`
  - GPU with 8GB+ VRAM
  - Training script using `DPOTrainer` or `KTOTrainer`

### 3. **GRPO/PPO Variants**
- **Less feasible locally**: Requires RL setup, reward models, extensive compute.
- **Alternative**: Use existing RLHF models or API-based approaches.

## Current Grokputer Context
- Primarily API-based (Grok), not local training
- Has some local inference (Qwen mentioned in docs)
- Multi-agent orchestration already resembles AsyncThink

For local training, start with DPO on a small model. Would need ~10-50GB disk space, GPU, and 1-2 days training time.</content>
<parameter name="filePath">LRN.MD