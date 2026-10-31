"""
Grokputer Training Module

Self-improvement through LoRA fine-tuning.

finetune_qlora pulls in torch, transformers and trl, so it is loaded on first use; `python -m src.training.rate` stays light.
"""

__all__ = ["train_qlora", "TrainingConfig"]


def __getattr__(name):
    if name in __all__:
        from . import finetune_qlora
        return getattr(finetune_qlora, name)
    raise AttributeError(name)
