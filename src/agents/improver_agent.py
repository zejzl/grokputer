"""
ImproverAgent for Grokputer (Phase 4 Self-Improving)
Applies ValidatorAgent recommendations; tunes params (e.g., OCR threshold) from Redis learnings.
Async for swarm; logs improvements for future cycles.
Best Practices: Typed, secure (data validation), edge-handled (no recs → skip).
"""

from typing import Dict, Any, List, Optional, TypedDict
import logging
import asyncio
import json  # For safe Redis storage
from src.core.message_bus import MessageBus  # Broadcasts
from src.observability.resource_monitor import ResourceMonitor  # Optional
from src.agents.validator_agent import ValidationResult  # For recs
from redis import Redis  # Direct Redis access

logger = logging.getLogger(__name__)

class LearningState(TypedDict):
    \"\"\"For Redis-stored learnings.\"\"\"
    task: str
    historical_scores: List[float]
    recommendations: List[str]
    tuned_params: Dict[str, Any]  # e.g., {\"ocr_conf_threshold\": 0.75}
    learned: bool  # Skip tuning if True (avg >80%, improvements >1)

class ImproverAgent:
    \"\"\"
    Self-improving agent: Applies fixes from validation, tunes via historical data.
    Max 3 improvements/cycle; stores in Redis for cross-run learning.
    \"\"\"
    def __init__(self, redis_url: str = \"redis://localhost:6379/0\", max_improvements: int = 3,
                 monitor: Optional[ResourceMonitor] = None):
        \"\"\"
        Init with Redis for learning storage.
        max_improvements: Per cycle limit.
        \"\"\"
        self.redis = Redis.from_url(redis_url)
        self.max_improvements = max_improvements
        self.monitor = monitor
        self.bus = MessageBus()
        self.logger = logger
        self.learning_prefix = \"grok_learning\"

    async def improve(self, state: Dict[str, Any], val_result: ValidationResult) -> Dict[str, Any]:
        \"\"\"
        Async improve: Apply recs, tune params, update state.
        Returns applied dict (e.g., {\"improved_ocr\": True, \"new_threshold\": 0.8}).
        Edges: No recs → {}; Invalid Redis → fallback defaults; Learned → skip.
        \"\"\"
        self.logger.info(\"[IMPROVER] Starting improvement phase\")
        if self.monitor:
            self.monitor.log_metrics(\"improver\")

        applied = {}
        recs = val_result.recommendations
        if not recs:
            self.logger.info(\"[IMPROVER] No recommendations - skipping\")
            return applied

        # Fetch historical learnings (Redis - JSON safe)
        task_key = f\"{self.learning_prefix}:recs_{state['task'][:50]}\"
        historical_json = self.redis.get(task_key)
        learning_state = LearningState(
            task=state['task'],
            historical_scores=[],
            recommendations=[],
            tuned_params={},
            learned=False
        )
        if historical_json:
            try:
                historical_data = json.loads(historical_json)
                learning_state.update(historical_data)
                self.logger.info(f\"[IMPROVER] Loaded historical: {len(learning_state['historical_scores'])} scores\")
            except json.JSONDecodeError as e:
                self.logger.warning(f\"[IMPROVER] Invalid Redis JSON: {e} - Using defaults\")

        # Skip if learned (self-optimize: Avoid over-tuning)
        historical_avg = sum(learning_state['historical_scores']) / len(learning_state['historical_scores']) if learning_state['historical_scores'] else 50
        if learning_state.get('learned', False) and historical_avg > 80:
            self.logger.info(f\"[IMPROVER] Learned mode - Skipping (avg {historical_avg:.1f}%)\")
            return applied

        improvements = 0
        for rec in recs[:self.max_improvements]:
            if \"Retry OCR\" in rec or \"low confidence\" in rec.lower():
                from src.screen_observer import ScreenObserver
                observer = ScreenObserver()
                # Tune threshold from history (self-improve: +0.05 if avg low, cap at 0.9)
                new_threshold = learning_state['tuned_params'].get('ocr_conf_threshold', 0.7)
                if historical_avg < 70 and len(learning_state['historical_scores']) > 2:
                    new_threshold = min(new_threshold + 0.05, 0.9)
                    learning_state['tuned_params']['ocr_conf_threshold'] = new_threshold
                    self.logger.info(f\"[IMPROVER] Tuned OCR threshold to {new_threshold} (history avg {historical_avg:.1f})\")
                observer.ocr_conf_threshold = new_threshold  # Set (extend ScreenObserver if needed)
                new_ocr = await asyncio.to_thread(observer.extract_text_from_screenshot)
                state['ocr_results'] = new_ocr
                applied[\"improved_ocr\"] = True
                applied[\"new_ocr_threshold\"] = new_threshold
                improvements += 1
                learning_state['historical_scores'].append(new_ocr.get('avg_confidence', 0) * 100)
                self.logger.info(f\"[IMPROVER] Improved OCR: New conf {new_ocr.get('avg_confidence', 0):.2f}\")

            elif \"Retry failed actions\" in rec:
                failed = [a for a in state.get('code_actions', []) if a.get(\"result\", [{}])[0].get(\"status\") != \"success\"]
                if failed:
                    from src.core.action_executor import ActionExecutor
                    executor = ActionExecutor()
                    retry_results = await asyncio.to_thread(executor.execute_tool_calls, [f['action'] for f in failed[:1]])  # Limit 1
                    for i, f in enumerate(failed[:1]):
                        idx = next((j for j, act in enumerate(state['code_actions']) if act == f), None)
                        if idx is not None:
                            state['code_actions'][idx] = {\"action\": f['action'], \"result\": retry_results[i]}
                    applied[\"retried_actions\"] = len(failed[:1])
                    improvements += 1
                    learning_state['recommendations'].append(\"action_retry_success\")  # Learn pattern
                    self.logger.info(f\"[IMPROVER] Retried {len(failed[:1])} actions\")

            elif \"High CPU\" in rec or \"High RAM\" in rec:
                # Resource optimization (self-improve: Tune monitor, clear cache)
                if self.monitor:
                    metrics = self.monitor.get_metrics()
                    if \"High CPU\" in rec and metrics['cpu_percent'] > 80:
                        new_interval = learning_state['tuned_params'].get('monitor_interval', 5) + 5  # Slow to 10s
                        new_interval = min(new_interval, 30)
                        learning_state['tuned_params']['monitor_interval'] = new_interval
                        self.monitor.log_interval = new_interval  # Set
                        applied[\"optimized_monitor\"] = True
                        applied[\"new_monitor_interval\"] = new_interval
                        improvements += 1
                        self.logger.info(f\"[IMPROVER] Tuned monitor interval to {new_interval}s for high CPU {metrics['cpu_percent']:.1f}%\")
+
                    if \"High RAM\" in rec and metrics['ram_percent'] > 75:
                        # Clear cache (e.g., messages to last 5)
                        state['messages'] = state['messages'][-5:] if len(state['messages']) > 5 else state['messages']
                        new_cache_size = learning_state['tuned_params'].get('cache_size', 10) - 5
                        new_cache_size = max(new_cache_size, 3)
                        learning_state['tuned_params']['cache_size'] = new_cache_size
                        applied[\"cleared_cache\"] = True
                        applied[\"new_cache_size\"] = new_cache_size
                        improvements += 1
                        self.logger.info(f\"[IMPROVER] Cleared cache to {new_cache_size} items for high RAM {metrics['ram_percent']:.1f}%\")
+
            elif \"Optimize workflow\" in rec:
                # Skip non-critical (e.g., reduce sub-tasks if too many)
                if len(state.get('sub_tasks', [])) > 5:
                    state['sub_tasks'] = state['sub_tasks'][:4]  # Limit to 4
                    applied[\"optimized_workflow\"] = True
                    improvements += 1
                    learning_state['recommendations'].append(\"workflow_optimized\")
                    self.logger.info(\"[IMPROVER] Optimized workflow: Limited sub-tasks to 4\")

        # Update learned flag (self-improve: If good history and improvements, learn)
        if improvements > 1 and historical_avg > 70:
            learning_state['learned'] = True
            self.logger.info(\"[IMPROVER] Marked as learned - Future skips possible\")

        # Store updated learnings (JSON safe)
        learning_state['recommendations'].append(recs[0])  # Add current rec
        try:
            self.redis.set(task_key, json.dumps(learning_state), ex=86400)  # 24h TTL
            self.logger.info(f\"[IMPROVER] Stored updated learnings: {task_key} (learned: {learning_state['learned']})\")
        except Exception as e:
            self.logger.error(f\"[IMPROVER] Redis store failed: {e}\")

        # Broadcast completion
        self.bus.broadcast({
            \"type\": \"improvement_complete\",
            \"applied\": applied,
            \"improvements\": improvements,
            \"historical_avg\": historical_avg,
            \"tuned_params\": learning_state['tuned_params']
        })
        self.logger.info(f\"[IMPROVER] Complete: {improvements} improvements applied, avg history {historical_avg:.1f}%\")

        if self.monitor:
            self.monitor.log_metrics(\"improver_end\")

        return applied

    async def finalize(self):
        \"\"\"Async cleanup (e.g., flush Redis if needed).\"\"\""
        self.logger.info(\"[IMPROVER] Finalizing - Learnings persisted\")
        # Future: Aggregate all keys for global tuning (e.g., avg across tasks)
        pass
