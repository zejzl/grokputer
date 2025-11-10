"""
Analyzer Agent - Performance metrics and system health monitoring for Pantheon.

Capabilities:
- Real-time performance monitoring
- Resource utilization tracking
- Success/failure rate analysis
- Bottleneck detection
- Agent health monitoring
- Performance report generation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import time

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance metric."""
    metric_name: str
    value: float
    unit: str
    timestamp: float
    agent_id: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class HealthStatus:
    """Agent health status."""
    agent_id: str
    status: str  # healthy, degraded, unhealthy, offline
    response_time_avg: float  # milliseconds
    success_rate: float  # percentage
    error_count: int
    last_heartbeat: float
    uptime: float  # seconds


@dataclass
class Bottleneck:
    """Identified performance bottleneck."""
    bottleneck_type: str  # agent, task, resource
    severity: str  # low, medium, high, critical
    description: str
    affected_component: str
    impact_score: float  # 0-100
    recommended_action: str


class AnalyzerAgent(BaseAgent):
    """
    Analyzer Agent (Phase 2): Monitors system performance and health.

    Features:
    - Real-time metrics collection
    - Agent health monitoring
    - Bottleneck detection
    - Performance trending
    - Report generation
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        session_logger: 'SessionLogger',
        config: Dict[str, Any],
        heartbeat_interval: float = 10.0
    ):
        super().__init__(agent_id, message_bus, session_logger, config, heartbeat_interval)

        # Metrics storage (time-series data)
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Agent health tracking
        self.agent_health: Dict[str, HealthStatus] = {}

        # Task performance tracking
        self.task_performance: Dict[str, List[float]] = defaultdict(list)
        self.task_outcomes: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})

        # Bottleneck detection
        self.bottlenecks: List[Bottleneck] = []

        # Configuration
        self.metric_retention = config.get("metric_retention_seconds", 3600)  # 1 hour
        self.health_check_interval = config.get("health_check_interval", 30.0)  # 30s
        self.bottleneck_threshold = config.get("bottleneck_threshold", 75.0)  # Impact score

        # Analysis task
        self.analysis_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats = {
            "metrics_collected": 0,
            "health_checks_performed": 0,
            "bottlenecks_detected": 0,
            "reports_generated": 0
        }

        self.session_logger.log_agent_init(
            self.agent_id,
            "Analyzer ready for performance monitoring"
        )

    async def process_message(self, message: Message) -> Optional[Dict]:
        """
        Process analyzer messages.

        Message types:
        - record_metric: Log performance metric
        - record_task: Log task execution performance
        - get_health: Get system health status
        - detect_bottlenecks: Trigger bottleneck detection
        - generate_report: Create performance report
        - get_stats: Return analyzer statistics
        """
        msg_type = message.message_type
        self._update_state("processing")

        try:
            if msg_type == "record_metric":
                return await self._record_metric(message.content)

            elif msg_type == "record_task":
                return await self._record_task_performance(message.content)

            elif msg_type == "get_health":
                return await self._get_health_status(message.content)

            elif msg_type == "detect_bottlenecks":
                return await self._detect_bottlenecks()

            elif msg_type == "generate_report":
                return await self._generate_report(message.content)

            elif msg_type == "get_stats":
                return self._get_stats()

            elif msg_type == "heartbeat":
                # Track agent heartbeats for health monitoring
                return await self._track_heartbeat(message.content)

            else:
                logger.warning(f"Unknown message type: {msg_type}")
                return {"status": "error", "reason": f"Unknown message type: {msg_type}"}

        finally:
            self._update_state("idle")

    async def _record_metric(self, content: Dict) -> Dict:
        """Record a performance metric."""
        metric = PerformanceMetric(
            metric_name=content.get("metric_name"),
            value=content.get("value", 0.0),
            unit=content.get("unit", ""),
            timestamp=content.get("timestamp", time.time()),
            agent_id=content.get("agent_id"),
            metadata=content.get("metadata", {})
        )

        # Store metric
        self.metrics[metric.metric_name].append(metric)
        self.stats["metrics_collected"] += 1

        # Cleanup old metrics
        await self._cleanup_old_metrics()

        return {
            "status": "recorded",
            "metric_name": metric.metric_name,
            "value": metric.value
        }

    async def _record_task_performance(self, content: Dict) -> Dict:
        """Record task execution performance."""
        task_type = content.get("task_type")
        execution_time = content.get("execution_time", 0.0)
        success = content.get("success", False)
        agent_id = content.get("agent_id")

        # Track performance
        self.task_performance[task_type].append(execution_time)

        # Track outcomes
        outcome_key = "success" if success else "failure"
        self.task_outcomes[task_type][outcome_key] += 1

        # Record as metric for time-series analysis
        await self._record_metric({
            "metric_name": f"task.{task_type}.execution_time",
            "value": execution_time,
            "unit": "seconds",
            "agent_id": agent_id,
            "metadata": {"success": success}
        })

        return {
            "status": "recorded",
            "task_type": task_type,
            "execution_time": execution_time
        }

    async def _track_heartbeat(self, content: Dict) -> Dict:
        """Track agent heartbeat for health monitoring."""
        agent_id = content.get("from") or content.get("agent_id")
        if not agent_id:
            return {"status": "error", "reason": "agent_id required"}

        current_time = time.time()

        # Update or create health status
        if agent_id in self.agent_health:
            health = self.agent_health[agent_id]
            health.last_heartbeat = current_time
        else:
            self.agent_health[agent_id] = HealthStatus(
                agent_id=agent_id,
                status="healthy",
                response_time_avg=0.0,
                success_rate=100.0,
                error_count=0,
                last_heartbeat=current_time,
                uptime=0.0
            )

        return {"status": "tracked"}

    async def _get_health_status(self, content: Dict) -> Dict:
        """Get system health status."""
        agent_filter = content.get("agent_id")  # Optional: specific agent

        current_time = time.time()
        health_statuses = []

        # Update health status based on metrics
        for agent_id, health in self.agent_health.items():
            if agent_filter and agent_id != agent_filter:
                continue

            # Check if agent is responsive
            time_since_heartbeat = current_time - health.last_heartbeat

            if time_since_heartbeat > 60:
                health.status = "offline"
            elif time_since_heartbeat > 30:
                health.status = "unhealthy"
            elif health.error_count > 5:
                health.status = "degraded"
            else:
                health.status = "healthy"

            # Calculate metrics from task performance
            agent_tasks = [
                k for k in self.task_performance.keys()
                if any(m.agent_id == agent_id for m in self.metrics.get(f"task.{k}.execution_time", []))
            ]

            if agent_tasks:
                # Average response time from recent tasks
                recent_times = []
                for task in agent_tasks:
                    metric_key = f"task.{task}.execution_time"
                    if metric_key in self.metrics:
                        recent_times.extend([m.value for m in list(self.metrics[metric_key])[-10:]])

                if recent_times:
                    health.response_time_avg = sum(recent_times) / len(recent_times) * 1000  # Convert to ms

            health_statuses.append(asdict(health))

        self.stats["health_checks_performed"] += 1

        return {
            "status": "success",
            "timestamp": current_time,
            "agents": health_statuses,
            "total_agents": len(health_statuses),
            "healthy_count": sum(1 for h in health_statuses if h["status"] == "healthy")
        }

    async def _detect_bottlenecks(self) -> Dict:
        """Detect performance bottlenecks."""
        bottlenecks = []
        current_time = time.time()

        # 1. Slow task detection
        for task_type, times in self.task_performance.items():
            if len(times) < 3:
                continue

            avg_time = sum(times) / len(times)
            recent_times = times[-10:]
            recent_avg = sum(recent_times) / len(recent_times)

            # Check if recently getting slower
            if recent_avg > avg_time * 1.5 and recent_avg > 5.0:
                impact = min((recent_avg / avg_time - 1) * 100, 100)
                bottleneck = Bottleneck(
                    bottleneck_type="task",
                    severity="high" if impact > 75 else "medium",
                    description=f"Task '{task_type}' execution time increased by {impact:.1f}%",
                    affected_component=task_type,
                    impact_score=impact,
                    recommended_action=f"Investigate recent changes or increase parallelization for {task_type}"
                )
                bottlenecks.append(bottleneck)

        # 2. Agent health bottlenecks
        for agent_id, health in self.agent_health.items():
            if health.status in ["degraded", "unhealthy"]:
                impact = 100 - health.success_rate
                bottleneck = Bottleneck(
                    bottleneck_type="agent",
                    severity="critical" if health.status == "unhealthy" else "high",
                    description=f"Agent '{agent_id}' is {health.status} (success rate: {health.success_rate:.1f}%)",
                    affected_component=agent_id,
                    impact_score=impact,
                    recommended_action=f"Restart or investigate {agent_id}"
                )
                bottlenecks.append(bottleneck)

        # 3. High failure rate detection
        for task_type, outcomes in self.task_outcomes.items():
            total = outcomes["success"] + outcomes["failure"]
            if total < 5:
                continue

            failure_rate = (outcomes["failure"] / total) * 100
            if failure_rate > 30:
                bottleneck = Bottleneck(
                    bottleneck_type="task",
                    severity="high" if failure_rate > 50 else "medium",
                    description=f"Task '{task_type}' has {failure_rate:.1f}% failure rate",
                    affected_component=task_type,
                    impact_score=failure_rate,
                    recommended_action=f"Review task execution logic for {task_type}"
                )
                bottlenecks.append(bottleneck)

        # Filter by threshold and update stored bottlenecks
        self.bottlenecks = [b for b in bottlenecks if b.impact_score >= self.bottleneck_threshold]
        self.stats["bottlenecks_detected"] = len(self.bottlenecks)

        return {
            "status": "analyzed",
            "bottlenecks_found": len(self.bottlenecks),
            "bottlenecks": [asdict(b) for b in self.bottlenecks],
            "timestamp": current_time
        }

    async def _generate_report(self, content: Dict) -> Dict:
        """Generate performance report."""
        report_type = content.get("type", "summary")  # summary, detailed, agent_specific
        time_range = content.get("time_range", 3600)  # Last hour by default

        current_time = time.time()
        start_time = current_time - time_range

        # Build report
        report = {
            "report_type": report_type,
            "generated_at": current_time,
            "time_range_seconds": time_range,
            "summary": {}
        }

        # 1. Overall metrics
        total_metrics = sum(len(m) for m in self.metrics.values())
        report["summary"]["total_metrics_collected"] = total_metrics
        report["summary"]["metric_types"] = len(self.metrics)

        # 2. Task performance summary
        task_summary = {}
        for task_type, times in self.task_performance.items():
            if not times:
                continue

            outcomes = self.task_outcomes[task_type]
            total_executions = outcomes["success"] + outcomes["failure"]

            task_summary[task_type] = {
                "total_executions": total_executions,
                "success_rate": (outcomes["success"] / total_executions * 100) if total_executions > 0 else 0,
                "avg_execution_time": sum(times) / len(times),
                "min_execution_time": min(times),
                "max_execution_time": max(times)
            }

        report["summary"]["tasks"] = task_summary

        # 3. Agent health summary
        health_summary = {
            "total_agents": len(self.agent_health),
            "healthy": sum(1 for h in self.agent_health.values() if h.status == "healthy"),
            "degraded": sum(1 for h in self.agent_health.values() if h.status == "degraded"),
            "unhealthy": sum(1 for h in self.agent_health.values() if h.status == "unhealthy"),
            "offline": sum(1 for h in self.agent_health.values() if h.status == "offline")
        }
        report["summary"]["agent_health"] = health_summary

        # 4. Bottlenecks
        report["summary"]["active_bottlenecks"] = len(self.bottlenecks)
        report["summary"]["critical_bottlenecks"] = sum(
            1 for b in self.bottlenecks if b.severity == "critical"
        )

        # 5. Detailed sections (if requested)
        if report_type == "detailed":
            report["detailed"] = {
                "bottlenecks": [asdict(b) for b in self.bottlenecks],
                "agent_health": [asdict(h) for h in self.agent_health.values()],
                "top_slow_tasks": sorted(
                    task_summary.items(),
                    key=lambda x: x[1]["avg_execution_time"],
                    reverse=True
                )[:5]
            }

        self.stats["reports_generated"] += 1

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Generated {report_type} report covering {time_range}s"
        )

        return {
            "status": "generated",
            "report": report
        }

    async def _cleanup_old_metrics(self):
        """Remove metrics older than retention period."""
        cutoff_time = time.time() - self.metric_retention

        for metric_name, metric_list in self.metrics.items():
            # Remove old metrics (deque is efficient for this)
            while metric_list and metric_list[0].timestamp < cutoff_time:
                metric_list.popleft()

    def _get_stats(self) -> Dict:
        """Return analyzer statistics."""
        return {
            "agent_id": self.agent_id,
            "stats": self.stats,
            "metrics_stored": sum(len(m) for m in self.metrics.values()),
            "agents_tracked": len(self.agent_health),
            "tasks_tracked": len(self.task_performance),
            "active_bottlenecks": len(self.bottlenecks)
        }

    async def on_start(self):
        """Analyzer-specific startup."""
        await super().on_start()

        # Start periodic analysis
        self.analysis_task = asyncio.create_task(self._periodic_analysis())

        self.session_logger.log_agent_ready(
            self.agent_id,
            "Analyzer monitoring active"
        )

    async def _periodic_analysis(self):
        """Periodic health checks and bottleneck detection."""
        while self.running:
            try:
                await asyncio.sleep(self.health_check_interval)

                # Run health check
                await self._get_health_status({})

                # Run bottleneck detection
                await self._detect_bottlenecks()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic analysis: {e}")

    async def on_stop(self):
        """Stop periodic analysis."""
        if self.analysis_task:
            self.analysis_task.cancel()
            try:
                await self.analysis_task
            except asyncio.CancelledError:
                pass

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Shutdown: {self.stats['metrics_collected']} metrics collected, "
            f"{self.stats['bottlenecks_detected']} bottlenecks detected"
        )
        await super().on_stop()
