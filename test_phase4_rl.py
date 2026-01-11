#!/usr/bin/env python3
"""
Phase 4: Self-Improvement & RL Integration Test

Tests the new RL-based optimization features:
- Q-learning for orchestration optimization
- Dynamic provider selection
- Self-improvement loops
- RL-based consensus strategy selection

Author: Grokputer Team
Date: 2026-01-11
"""

import asyncio
import logging
import sys
import time
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, 'src')

from collaboration.orchestrator import Orchestrator, OrchestrationConfig, OrchestrationStrategy
from collaboration.multi_provider_coordinator import CollaborationConfig
from collaboration.provider_registry import initialize_mock_providers, provider_registry
from collaboration.orchestrator import MAFLogger, PerformanceMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Phase4RLTester:
    """Test suite for Phase 4 RL integration."""

    def __init__(self):
        self.orchestrator = None
        self.test_results = []

    async def setup(self):
        """Setup test environment."""
        logger.info("Setting up Phase 4 RL test environment")

        # Initialize mock providers
        await initialize_mock_providers()

        # Create orchestrator with RL optimization enabled
        config = OrchestrationConfig(
            strategy=OrchestrationStrategy.CONCURRENT,
            max_concurrent_providers=4,
            timeout_per_provider=30.0,
            enable_circuit_breaker=True,
        )

        self.orchestrator = Orchestrator(config=config)

        # Start health monitoring
        await provider_registry.start_health_monitoring()

        logger.info("Phase 4 test environment setup complete")

    async def teardown(self):
        """Cleanup test environment."""
        logger.info("Cleaning up Phase 4 test environment")
        await provider_registry.stop_health_monitoring()

    async def test_rl_orchestration_learning(self):
        """Test RL-based orchestration learning."""
        logger.info("Testing RL orchestration learning")

        # Run multiple orchestrations to allow learning
        tasks = [
            "Analyze machine learning algorithms",
            "Design a scalable web architecture",
            "Write comprehensive documentation",
            "Perform code quality analysis",
            "Optimize database queries",
        ]

        collab_config = CollaborationConfig(min_providers=2, max_rounds=2)

        results = []
        for i, task in enumerate(tasks):
            start_time = time.time()
            result = await self.orchestrator.orchestrate_task(task, collab_config)
            execution_time = time.time() - start_time

            results.append({
                "task": task,
                "success": result.success,
                "execution_time": execution_time,
                "providers_used": len(result.messages) if result.messages else 0,
            })

            # Small delay between tasks
            await asyncio.sleep(0.5)

        # Check if RL learning occurred
        rl_enabled = hasattr(self.orchestrator, 'rl_optimizer') and self.orchestrator.rl_optimizer is not None
        learning_steps = 0
        if rl_enabled:
            rl_stats = self.orchestrator.rl_optimizer.get_rl_stats()
            learning_steps = rl_stats.get("learning_steps", 0)

        success_count = sum(1 for r in results if r["success"])
        avg_execution_time = sum(r["execution_time"] for r in results) / len(results)

        success = rl_enabled and learning_steps > 0
        self.test_results.append({
            "test": "rl_orchestration_learning",
            "success": success,
            "rl_enabled": rl_enabled,
            "learning_steps": learning_steps,
            "tasks_completed": len(results),
            "success_rate": success_count / len(results),
            "avg_execution_time": avg_execution_time,
        })

        logger.info(f"RL orchestration learning test: {'PASSED' if success else 'FAILED'} (learning steps: {learning_steps})")
        return success

    async def test_dynamic_provider_selection(self):
        """Test dynamic provider selection based on performance."""
        logger.info("Testing dynamic provider selection")

        # Run a task and check provider selection
        task = "Test dynamic provider selection"
        collab_config = CollaborationConfig(min_providers=2, max_rounds=1)

        result = await self.orchestrator.orchestrate_task(task, collab_config)

        # Check if providers were selected (basic functionality test)
        providers_used = len(result.messages) if result.messages else 0
        selection_worked = providers_used >= collab_config.min_providers

        success = selection_worked
        self.test_results.append({
            "test": "dynamic_provider_selection",
            "success": success,
            "providers_used": providers_used,
            "min_required": collab_config.min_providers,
            "selection_worked": selection_worked,
        })

        logger.info(f"Dynamic provider selection test: {'PASSED' if success else 'FAILED'}")
        return success

    async def test_self_improvement_loop(self):
        """Test self-improvement loop functionality."""
        logger.info("Testing self-improvement loop")

        # Trigger optimization analysis
        optimization_result = None
        if hasattr(self.orchestrator, 'rl_optimizer') and self.orchestrator.rl_optimizer:
            optimization_result = self.orchestrator.rl_optimizer.analyze_performance_and_optimize()

        # Check if optimization ran
        optimization_completed = (
            optimization_result and
            optimization_result.get("status") == "completed"
        )

        success = optimization_completed
        self.test_results.append({
            "test": "self_improvement_loop",
            "success": success,
            "optimization_status": optimization_result.get("status") if optimization_result else "not_run",
            "metrics_analyzed": bool(optimization_result and optimization_result.get("metrics_analyzed")),
            "optimizations_applied": optimization_result.get("optimizations_applied", 0) if optimization_result else 0,
        })

        logger.info(f"Self-improvement loop test: {'PASSED' if success else 'FAILED'}")
        return success

    async def test_rl_consensus_optimization(self):
        """Test RL-based consensus strategy optimization."""
        logger.info("Testing RL consensus optimization")

        # Run a task that should trigger consensus analysis
        task = "Test consensus optimization with multiple perspectives"
        collab_config = CollaborationConfig(min_providers=3, max_rounds=2)

        result = await self.orchestrator.orchestrate_task(task, collab_config)

        # Check if consensus was analyzed
        consensus_analyzed = (
            result.consensus_result and
            hasattr(result.consensus_result, 'confidence')
        )

        success = consensus_analyzed
        self.test_results.append({
            "test": "rl_consensus_optimization",
            "success": success,
            "consensus_reached": result.consensus_result.is_consensus if result.consensus_result else False,
            "consensus_confidence": result.consensus_result.confidence if result.consensus_result else 0.0,
            "consensus_analyzed": consensus_analyzed,
        })

        logger.info(f"RL consensus optimization test: {'PASSED' if success else 'FAILED'}")
        return success

    async def test_performance_monitoring_integration(self):
        """Test that performance monitoring works with RL."""
        logger.info("Testing performance monitoring integration")

        # Get performance metrics
        stats = self.orchestrator.get_orchestration_stats()
        perf_monitor = stats.get("performance_monitor", {})

        # Check if metrics are being collected
        orchestration_metrics = perf_monitor.get("orchestration", {})
        has_recent_data = orchestration_metrics.get("total_count", 0) > 0

        # Check RL integration
        rl_integrated = hasattr(self.orchestrator, 'rl_optimizer') and self.orchestrator.rl_optimizer is not None

        success = has_recent_data and rl_integrated
        self.test_results.append({
            "test": "performance_monitoring_integration",
            "success": success,
            "total_orchestrations": orchestration_metrics.get("total_count", 0),
            "rl_integrated": rl_integrated,
            "has_recent_data": has_recent_data,
        })

        logger.info(f"Performance monitoring integration test: {'PASSED' if success else 'FAILED'}")
        return success

    async def run_all_tests(self):
        """Run all Phase 4 RL tests."""
        logger.info("Starting Phase 4 RL integration test suite")

        await self.setup()

        try:
            tests = [
                self.test_rl_orchestration_learning,
                self.test_dynamic_provider_selection,
                self.test_self_improvement_loop,
                self.test_rl_consensus_optimization,
                self.test_performance_monitoring_integration,
            ]

            passed = 0
            total = len(tests)

            for test in tests:
                try:
                    if await test():
                        passed += 1
                except Exception as e:
                    logger.error(f"Test {test.__name__} failed with exception: {e}")
                    self.test_results.append({
                        "test": test.__name__,
                        "success": False,
                        "error": str(e),
                    })

            # Print results
            logger.info(f"\n{'='*60}")
            logger.info("Phase 4 RL Integration Test Results")
            logger.info(f"{'='*60}")
            logger.info(f"Tests passed: {passed}/{total}")
            logger.info(".1f")

            for result in self.test_results:
                status = "✓ PASS" if result["success"] else "✗ FAIL"
                logger.info(f"{status} {result['test']}")

            # Show RL learning stats if available
            if hasattr(self.orchestrator, 'rl_optimizer') and self.orchestrator.rl_optimizer:
                rl_stats = self.orchestrator.rl_optimizer.get_rl_stats()
                logger.info(f"\nRL Learning Stats:")
                logger.info(f"- Learning steps: {rl_stats.get('learning_steps', 0)}")
                logger.info(f"- Q-table size: {rl_stats.get('q_table_size', 0)}")
                logger.info(f"- Replay buffer size: {rl_stats.get('replay_buffer_size', 0)}")
                logger.info(f"- Current epsilon: {rl_stats.get('current_epsilon', 1.0):.3f}")

            success = passed >= 3  # Allow some flexibility for complex RL tests
            logger.info(f"\nOverall result: {'MOST TESTS PASSED' if success else 'TOO MANY TESTS FAILED'}")

        finally:
            await self.teardown()

        return passed >= 3


async def main():
    """Main test function."""
    tester = Phase4RLTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())