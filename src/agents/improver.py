"""
Improver Agent - Self-optimization and continuous improvement for Pantheon.

Capabilities:
- Analyzes performance data from Analyzer
- Leverages learned patterns from Learner
- Suggests code/config optimizations
- Applies safe automated improvements
- Tracks improvement history
- Generates improvement reports
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import json

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority

logger = logging.getLogger(__name__)


@dataclass
class Improvement:
    """Represents a suggested or applied improvement."""
    improvement_id: str
    category: str  # performance, reliability, efficiency, safety
    severity: str  # low, medium, high, critical
    description: str
    current_state: str
    proposed_state: str
    expected_impact: str
    confidence: float  # 0-100%
    source_data: List[str]  # References to analyzer/learner data
    auto_applicable: bool  # Can be auto-applied safely
    status: str  # suggested, applied, rejected, failed
    created_at: float
    applied_at: Optional[float] = None
    result: Optional[str] = None


@dataclass
class OptimizationResult:
    """Result of applying an optimization."""
    improvement_id: str
    success: bool
    before_metrics: Dict[str, float]
    after_metrics: Dict[str, float]
    improvement_percentage: float
    details: str


class ImproverAgent(BaseAgent):
    """
    Improver Agent (Phase 2): Self-optimization and continuous improvement.

    Features:
    - Performance optimization suggestions
    - Automated safe improvements
    - Configuration tuning
    - Improvement tracking
    - Impact measurement
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

        # Improvement storage
        self.improvements: Dict[str, Improvement] = {}  # improvement_id -> Improvement
        self.optimization_results: List[OptimizationResult] = []

        # Configuration
        self.auto_apply_threshold = config.get("auto_apply_threshold", 85.0)  # Confidence %
        self.max_improvements_per_session = config.get("max_improvements_per_session", 5)
        self.enable_auto_apply = config.get("enable_auto_apply", False)

        # Statistics
        self.stats = {
            "improvements_suggested": 0,
            "improvements_applied": 0,
            "improvements_rejected": 0,
            "optimizations_succeeded": 0,
            "optimizations_failed": 0
        }

        self.session_logger.log_agent_init(
            self.agent_id,
            f"Improver ready (auto_apply={self.enable_auto_apply})"
        )

    async def process_message(self, message: Message) -> Optional[Dict]:
        """
        Process improvement messages.

        Message types:
        - analyze_for_improvements: Analyze system for optimization opportunities
        - suggest_improvement: Get specific improvement suggestion
        - apply_improvement: Apply a specific improvement
        - get_improvements: List all improvements
        - measure_impact: Measure impact of applied improvements
        - get_stats: Return improver statistics
        """
        msg_type = message.message_type
        self._update_state("processing")

        try:
            if msg_type == "analyze_for_improvements":
                return await self._analyze_for_improvements(message.content)

            elif msg_type == "suggest_improvement":
                return await self._suggest_improvement(message.content)

            elif msg_type == "apply_improvement":
                return await self._apply_improvement(message.content)

            elif msg_type == "get_improvements":
                return await self._get_improvements(message.content)

            elif msg_type == "measure_impact":
                return await self._measure_impact(message.content)

            elif msg_type == "get_stats":
                return self._get_stats()

            else:
                logger.warning(f"Unknown message type: {msg_type}")
                return {"status": "error", "reason": f"Unknown message type: {msg_type}"}

        finally:
            self._update_state("idle")

    async def _analyze_for_improvements(self, content: Dict) -> Dict:
        """
        Analyze system for improvement opportunities.

        Integrates data from Analyzer and Learner.
        """
        improvements_found = []

        # 1. Request analyzer data
        analyzer_request = Message(
            message_type="detect_bottlenecks",
            from_agent=self.agent_id,
            to_agent="analyzer",
            priority=MessagePriority.NORMAL,
            content={}
        )

        try:
            analyzer_response = await self.message_bus.send_and_wait(
                "analyzer",
                analyzer_request,
                timeout=10.0
            )

            if analyzer_response and analyzer_response.get("bottlenecks"):
                # Convert bottlenecks to improvements
                for bottleneck in analyzer_response["bottlenecks"]:
                    improvement = await self._bottleneck_to_improvement(bottleneck)
                    if improvement:
                        improvements_found.append(improvement)
        except asyncio.TimeoutError:
            logger.warning("Analyzer timeout - proceeding without bottleneck data")

        # 2. Request learner insights
        learner_request = Message(
            message_type="get_insights",
            from_agent=self.agent_id,
            to_agent="learner",
            priority=MessagePriority.NORMAL,
            content={"type": "optimization", "min_confidence": 70.0}
        )

        try:
            learner_response = await self.message_bus.send_and_wait(
                "learner",
                learner_request,
                timeout=10.0
            )

            if learner_response and learner_response.get("insights"):
                # Convert insights to improvements
                for insight in learner_response["insights"]:
                    improvement = await self._insight_to_improvement(insight)
                    if improvement:
                        improvements_found.append(improvement)
        except asyncio.TimeoutError:
            logger.warning("Learner timeout - proceeding without insight data")

        # 3. Apply generic optimization rules
        generic_improvements = await self._generate_generic_improvements()
        improvements_found.extend(generic_improvements)

        # Store improvements
        for improvement in improvements_found:
            self.improvements[improvement.improvement_id] = improvement
            self.stats["improvements_suggested"] += 1

            # Auto-apply if enabled and confidence is high
            if (self.enable_auto_apply and
                improvement.auto_applicable and
                improvement.confidence >= self.auto_apply_threshold):

                await self._apply_improvement({"improvement_id": improvement.improvement_id})

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Analysis complete: {len(improvements_found)} improvements suggested"
        )

        return {
            "status": "analyzed",
            "improvements_found": len(improvements_found),
            "improvements": [asdict(imp) for imp in improvements_found],
            "auto_applied": sum(
                1 for imp in improvements_found
                if imp.status == "applied"
            )
        }

    async def _bottleneck_to_improvement(self, bottleneck: Dict) -> Optional[Improvement]:
        """Convert analyzer bottleneck to improvement suggestion."""
        improvement_id = f"bottleneck_{bottleneck['bottleneck_type']}_{hash(bottleneck['description']) % 10000}"

        # Map severity
        severity_map = {"low": "medium", "medium": "high", "high": "critical", "critical": "critical"}
        severity = severity_map.get(bottleneck.get("severity", "medium"), "medium")

        # Determine if auto-applicable (only for config changes, not code)
        auto_applicable = bottleneck["bottleneck_type"] == "task" and bottleneck["impact_score"] < 50

        improvement = Improvement(
            improvement_id=improvement_id,
            category="performance",
            severity=severity,
            description=bottleneck["description"],
            current_state=f"Component '{bottleneck['affected_component']}' has performance issues",
            proposed_state=bottleneck["recommended_action"],
            expected_impact=f"Reduce impact by {bottleneck['impact_score']:.1f}%",
            confidence=min(bottleneck["impact_score"], 95.0),
            source_data=[f"analyzer_bottleneck:{bottleneck.get('bottleneck_type')}"],
            auto_applicable=auto_applicable,
            status="suggested",
            created_at=datetime.now().timestamp()
        )

        return improvement

    async def _insight_to_improvement(self, insight: Dict) -> Optional[Improvement]:
        """Convert learner insight to improvement suggestion."""
        improvement_id = f"insight_{insight['insight_type']}_{hash(insight['description']) % 10000}"

        # Map insight type to category
        category_map = {
            "optimization": "efficiency",
            "warning": "reliability",
            "suggestion": "performance"
        }
        category = category_map.get(insight.get("insight_type"), "efficiency")

        improvement = Improvement(
            improvement_id=improvement_id,
            category=category,
            severity="medium",
            description=insight["description"],
            current_state="Current execution pattern is suboptimal",
            proposed_state=insight["recommended_action"],
            expected_impact="Improve execution based on learned patterns",
            confidence=insight["confidence"],
            source_data=[f"learner_insight:{p}" for p in insight.get("supporting_patterns", [])],
            auto_applicable=insight["confidence"] > 85 and insight["insight_type"] == "optimization",
            status="suggested",
            created_at=datetime.now().timestamp()
        )

        return improvement

    async def _generate_generic_improvements(self) -> List[Improvement]:
        """Generate generic optimization suggestions."""
        improvements = []

        # Example: Suggest batch processing if many sequential tasks
        # Example: Suggest caching if repeated operations
        # Example: Suggest parallel execution if independent tasks
        # This would be expanded based on actual system analysis

        # Placeholder for now
        generic = Improvement(
            improvement_id="generic_001",
            category="efficiency",
            severity="low",
            description="Consider enabling result caching for repeated operations",
            current_state="No caching enabled",
            proposed_state="Enable LRU cache for frequently accessed data",
            expected_impact="Reduce redundant computations by ~20%",
            confidence=70.0,
            source_data=["generic_optimization_rules"],
            auto_applicable=False,
            status="suggested",
            created_at=datetime.now().timestamp()
        )
        improvements.append(generic)

        return improvements

    async def _suggest_improvement(self, content: Dict) -> Dict:
        """Get specific improvement suggestion for a component."""
        component = content.get("component")
        category = content.get("category", "all")

        if not component:
            return {"status": "error", "reason": "component required"}

        # Find relevant improvements
        relevant = [
            imp for imp in self.improvements.values()
            if component in imp.description and
            (category == "all" or imp.category == category)
        ]

        # Sort by confidence
        relevant.sort(key=lambda x: x.confidence, reverse=True)

        return {
            "status": "success",
            "component": component,
            "suggestions": [asdict(imp) for imp in relevant[:5]],
            "total_found": len(relevant)
        }

    async def _apply_improvement(self, content: Dict) -> Dict:
        """Apply a specific improvement."""
        improvement_id = content.get("improvement_id")

        if not improvement_id or improvement_id not in self.improvements:
            return {"status": "error", "reason": "Invalid improvement_id"}

        improvement = self.improvements[improvement_id]

        if improvement.status == "applied":
            return {"status": "already_applied", "improvement_id": improvement_id}

        # Capture before metrics (if analyzer available)
        before_metrics = await self._capture_metrics()

        # Apply the improvement
        success = False
        result_details = ""

        try:
            if improvement.category == "performance":
                success, result_details = await self._apply_performance_improvement(improvement)
            elif improvement.category == "efficiency":
                success, result_details = await self._apply_efficiency_improvement(improvement)
            elif improvement.category == "reliability":
                success, result_details = await self._apply_reliability_improvement(improvement)
            else:
                result_details = "Improvement type not yet implemented"
                success = False

        except Exception as e:
            success = False
            result_details = f"Error applying improvement: {str(e)}"
            logger.error(f"Improvement application failed: {e}")

        # Update improvement status
        improvement.status = "applied" if success else "failed"
        improvement.applied_at = datetime.now().timestamp()
        improvement.result = result_details

        # Capture after metrics
        after_metrics = await self._capture_metrics()

        # Create optimization result
        if success:
            opt_result = OptimizationResult(
                improvement_id=improvement_id,
                success=True,
                before_metrics=before_metrics,
                after_metrics=after_metrics,
                improvement_percentage=self._calculate_improvement(before_metrics, after_metrics),
                details=result_details
            )
            self.optimization_results.append(opt_result)
            self.stats["optimizations_succeeded"] += 1
            self.stats["improvements_applied"] += 1
        else:
            self.stats["optimizations_failed"] += 1
            self.stats["improvements_rejected"] += 1

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"{'Applied' if success else 'Failed'} improvement: {improvement_id}"
        )

        return {
            "status": "applied" if success else "failed",
            "improvement_id": improvement_id,
            "success": success,
            "details": result_details,
            "before_metrics": before_metrics,
            "after_metrics": after_metrics
        }

    async def _apply_performance_improvement(self, improvement: Improvement) -> Tuple[bool, str]:
        """Apply a performance-related improvement."""
        # Placeholder - would implement actual performance optimizations
        # Examples: Adjust batch sizes, enable parallelization, tune timeouts

        details = f"Performance improvement simulated: {improvement.proposed_state}"
        return True, details

    async def _apply_efficiency_improvement(self, improvement: Improvement) -> Tuple[bool, str]:
        """Apply an efficiency-related improvement."""
        # Placeholder - would implement actual efficiency optimizations
        # Examples: Enable caching, reduce redundant operations

        details = f"Efficiency improvement simulated: {improvement.proposed_state}"
        return True, details

    async def _apply_reliability_improvement(self, improvement: Improvement) -> Tuple[bool, str]:
        """Apply a reliability-related improvement."""
        # Placeholder - would implement actual reliability optimizations
        # Examples: Add retries, improve error handling

        details = f"Reliability improvement simulated: {improvement.proposed_state}"
        return True, details

    async def _capture_metrics(self) -> Dict[str, float]:
        """Capture current system metrics."""
        metrics = {
            "timestamp": datetime.now().timestamp(),
            "placeholder_metric": 0.0
        }

        # Request from analyzer if available
        try:
            analyzer_request = Message(
                message_type="get_stats",
                from_agent=self.agent_id,
                to_agent="analyzer",
                priority=MessagePriority.NORMAL,
                content={}
            )

            response = await self.message_bus.send_and_wait(
                "analyzer",
                analyzer_request,
                timeout=5.0
            )

            if response and "stats" in response:
                metrics.update(response["stats"])
        except:
            pass  # Proceed with placeholder metrics

        return metrics

    def _calculate_improvement(self, before: Dict, after: Dict) -> float:
        """Calculate improvement percentage between metrics."""
        # Simplified calculation - would be more sophisticated in production
        if not before or not after:
            return 0.0

        # Example: Compare response times if available
        before_val = before.get("avg_response_time", 1.0)
        after_val = after.get("avg_response_time", 1.0)

        if before_val == 0:
            return 0.0

        improvement = ((before_val - after_val) / before_val) * 100
        return max(0.0, improvement)

    async def _get_improvements(self, content: Dict) -> Dict:
        """List improvements with optional filters."""
        status_filter = content.get("status", "all")  # all, suggested, applied, failed
        category_filter = content.get("category", "all")

        filtered = [
            imp for imp in self.improvements.values()
            if (status_filter == "all" or imp.status == status_filter) and
            (category_filter == "all" or imp.category == category_filter)
        ]

        # Sort by confidence
        filtered.sort(key=lambda x: x.confidence, reverse=True)

        return {
            "status": "success",
            "improvements": [asdict(imp) for imp in filtered],
            "total": len(filtered)
        }

    async def _measure_impact(self, content: Dict) -> Dict:
        """Measure impact of applied improvements."""
        if not self.optimization_results:
            return {
                "status": "no_data",
                "message": "No improvements have been applied yet"
            }

        total_improvements = len(self.optimization_results)
        successful = sum(1 for r in self.optimization_results if r.success)
        avg_improvement = sum(r.improvement_percentage for r in self.optimization_results) / total_improvements

        return {
            "status": "success",
            "total_optimizations": total_improvements,
            "successful": successful,
            "failed": total_improvements - successful,
            "average_improvement_percentage": avg_improvement,
            "results": [asdict(r) for r in self.optimization_results[-10:]]  # Last 10
        }

    def _get_stats(self) -> Dict:
        """Return improver statistics."""
        return {
            "agent_id": self.agent_id,
            "stats": self.stats,
            "improvements_tracked": len(self.improvements),
            "optimization_results": len(self.optimization_results),
            "auto_apply_enabled": self.enable_auto_apply
        }

    async def on_start(self):
        """Improver-specific startup."""
        await super().on_start()
        self.session_logger.log_agent_ready(
            self.agent_id,
            "Improver active - continuous optimization enabled"
        )

    async def on_stop(self):
        """Persist improvements before shutdown."""
        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Shutdown: {self.stats['improvements_suggested']} suggested, "
            f"{self.stats['improvements_applied']} applied, "
            f"{self.stats['optimizations_succeeded']} succeeded"
        )
        await super().on_stop()
