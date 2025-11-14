"""
Agent Lifecycle Management System

Provides comprehensive monitoring, health checking, deadlock detection,
and automated restart capabilities for all agents in the Grokputer system.
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json

from src.core.base_agent import BaseAgent
from src.observability.deadlock_detector import DeadlockDetector
from src.observability.session_logger import SessionLogger

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent lifecycle status enumeration."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RESTARTING = "restarting"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class AgentHealthMetrics:
    """Health metrics for an agent."""
    agent_id: str
    status: AgentStatus = AgentStatus.INITIALIZING
    last_health_check: float = field(default_factory=time.time)
    consecutive_failures: int = 0
    total_restarts: int = 0
    uptime_seconds: float = 0.0
    last_error: Optional[str] = None
    performance_score: float = 1.0  # 0.0 to 1.0

    # Advanced metrics
    cpu_usage_history: List[float] = field(default_factory=list)
    memory_usage_history: List[float] = field(default_factory=list)
    response_times: List[float] = field(default_factory=list)
    message_throughput: float = 0.0
    load_factor: float = 1.0
    predictive_failure_risk: float = 0.0  # 0.0 to 1.0

    def update_health(self, is_healthy: bool, error: Optional[str] = None):
        """Update health status."""
        self.last_health_check = time.time()

        if is_healthy:
            self.consecutive_failures = 0
            if self.status in [AgentStatus.UNHEALTHY, AgentStatus.DEGRADED]:
                self.status = AgentStatus.HEALTHY
        else:
            self.consecutive_failures += 1
            self.last_error = error
            if self.consecutive_failures >= 3:
                self.status = AgentStatus.UNHEALTHY
            elif self.consecutive_failures >= 1:
                self.status = AgentStatus.DEGRADED


@dataclass
class LifecycleConfig:
    """Configuration for agent lifecycle management."""
    health_check_interval: float = 30.0  # seconds
    max_restart_attempts: int = 3
    restart_delay_seconds: float = 5.0
    unhealthy_threshold: int = 3  # consecutive failures
    degraded_threshold: int = 1
    auto_restart_enabled: bool = True
    deadlock_timeout_seconds: float = 60.0
    performance_monitoring: bool = True

    # Advanced features
    auto_scaling_enabled: bool = True
    predictive_monitoring: bool = True
    max_agents_per_type: int = 5
    min_agents_per_type: int = 1
    scaling_threshold_high: float = 0.8  # Scale up when load > 80%
    scaling_threshold_low: float = 0.3   # Scale down when load < 30%
    emergency_shutdown_threshold: float = 0.95  # System load emergency


class AgentLifecycleManager:
    """
    Comprehensive agent lifecycle management system.

    Features:
    - Health monitoring for all registered agents
    - Automated restart on failures
    - Deadlock detection and recovery
    - Performance tracking
    - Graceful shutdown coordination
    """

    def __init__(
        self,
        config: LifecycleConfig = None,
        session_logger: SessionLogger = None
    ):
        self.config = config or LifecycleConfig()
        self.session_logger = session_logger

        # Agent tracking
        self.agents: Dict[str, BaseAgent] = {}
        self.health_metrics: Dict[str, AgentHealthMetrics] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {}

        # Monitoring infrastructure
        self.deadlock_detector = DeadlockDetector(
            timeout_seconds=self.config.deadlock_timeout_seconds,
            check_interval=10.0
        )

        # Control flags
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_agent_failure: Optional[Callable[[str, str], None]] = None
        self.on_agent_restart: Optional[Callable[[str], None]] = None
        self.on_system_health_change: Optional[Callable[[str], None]] = None

        logger.info("[LifecycleManager] Initialized with config: health_check=%ss, auto_restart=%s",
                   self.config.health_check_interval, self.config.auto_restart_enabled)

    async def register_agent(self, agent: BaseAgent) -> bool:
        """
        Register an agent for lifecycle management.

        Args:
            agent: The agent to register

        Returns:
            True if registration successful
        """
        agent_id = agent.agent_id

        if agent_id in self.agents:
            logger.warning(f"[LifecycleManager] Agent {agent_id} already registered")
            return False

        # Register with manager
        self.agents[agent_id] = agent
        self.health_metrics[agent_id] = AgentHealthMetrics(agent_id=agent_id)

        # Register with deadlock detector
        self.deadlock_detector.register_agent(agent_id)

        # Set deadlock detector reference in agent
        agent.deadlock_detector = self.deadlock_detector

        logger.info(f"[LifecycleManager] Registered agent: {agent_id}")
        if self.session_logger:
            self.session_logger.log_agent_start(agent_id, "registered")

        return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from lifecycle management.

        Args:
            agent_id: ID of agent to unregister

        Returns:
            True if unregistration successful
        """
        if agent_id not in self.agents:
            logger.warning(f"[LifecycleManager] Agent {agent_id} not registered")
            return False

        # Stop agent if running
        if agent_id in self.agent_tasks:
            await self._stop_agent_task(agent_id)

        # Remove from tracking
        del self.agents[agent_id]
        del self.health_metrics[agent_id]
        self.deadlock_detector.unregister_agent(agent_id)

        logger.info(f"[LifecycleManager] Unregistered agent: {agent_id}")
        if self.session_logger:
            self.session_logger.log_agent_stop(agent_id, "unregistered")

        return True

    async def start_all_agents(self) -> bool:
        """
        Start all registered agents.

        Returns:
            True if all agents started successfully
        """
        logger.info(f"[LifecycleManager] Starting {len(self.agents)} agents")

        success_count = 0
        for agent_id, agent in self.agents.items():
            if await self._start_agent(agent_id):
                success_count += 1

        logger.info(f"[LifecycleManager] Started {success_count}/{len(self.agents)} agents")

        # Start monitoring if not already running
        if not self.running:
            await self.start_monitoring()

        return success_count == len(self.agents)

    async def stop_all_agents(self) -> bool:
        """
        Stop all registered agents gracefully.

        Returns:
            True if all agents stopped successfully
        """
        logger.info(f"[LifecycleManager] Stopping {len(self.agents)} agents")

        stop_tasks = []
        for agent_id in list(self.agent_tasks.keys()):
            stop_tasks.append(self._stop_agent_task(agent_id))

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        # Stop monitoring
        await self.stop_monitoring()

        logger.info("[LifecycleManager] All agents stopped")
        return True

    async def start_monitoring(self):
        """Start the monitoring system."""
        if self.running:
            return

        self.running = True

        # Start deadlock detector
        await self.deadlock_detector.start()

        # Start health monitoring
        self.health_check_task = asyncio.create_task(self._health_monitor_loop())

        logger.info("[LifecycleManager] Monitoring started")

    async def stop_monitoring(self):
        """Stop the monitoring system."""
        if not self.running:
            return

        self.running = False

        # Stop deadlock detector
        await self.deadlock_detector.stop()

        # Stop health monitoring
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        logger.info("[LifecycleManager] Monitoring stopped")

    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health status.

        Returns:
            Dictionary with system health information
        """
        total_agents = len(self.agents)
        healthy_count = sum(1 for m in self.health_metrics.values()
                          if m.status in [AgentStatus.HEALTHY, AgentStatus.RUNNING])
        degraded_count = sum(1 for m in self.health_metrics.values()
                           if m.status == AgentStatus.DEGRADED)
        unhealthy_count = sum(1 for m in self.health_metrics.values()
                            if m.status == AgentStatus.UNHEALTHY)

        overall_status = "healthy"
        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"

        return {
            "overall_status": overall_status,
            "total_agents": total_agents,
            "healthy_agents": healthy_count,
            "degraded_agents": degraded_count,
            "unhealthy_agents": unhealthy_count,
            "agent_details": {
                agent_id: {
                    "status": metrics.status.value,
                    "consecutive_failures": metrics.consecutive_failures,
                    "total_restarts": metrics.total_restarts,
                    "uptime_seconds": metrics.uptime_seconds,
                    "last_error": metrics.last_error,
                    "performance_score": metrics.performance_score
                }
                for agent_id, metrics in self.health_metrics.items()
            },
            "deadlock_stats": self.deadlock_detector.get_stats()
        }

    async def restart_agent(self, agent_id: str, reason: str = "manual") -> bool:
        """
        Manually restart a specific agent.

        Args:
            agent_id: ID of agent to restart
            reason: Reason for restart

        Returns:
            True if restart successful
        """
        logger.info(f"[LifecycleManager] Manual restart requested for {agent_id}: {reason}")

        if agent_id not in self.agents:
            logger.error(f"[LifecycleManager] Cannot restart unknown agent: {agent_id}")
            return False

        # Stop current instance
        await self._stop_agent_task(agent_id)

        # Start new instance
        success = await self._start_agent(agent_id)

        if success:
            metrics = self.health_metrics[agent_id]
            metrics.total_restarts += 1
            logger.info(f"[LifecycleManager] Successfully restarted agent: {agent_id}")
            if self.on_agent_restart:
                await self.on_agent_restart(agent_id)
        else:
            logger.error(f"[LifecycleManager] Failed to restart agent: {agent_id}")

        return success

    async def _start_agent(self, agent_id: str) -> bool:
        """
        Start a specific agent.

        Args:
            agent_id: ID of agent to start

        Returns:
            True if agent started successfully
        """
        agent = self.agents[agent_id]
        metrics = self.health_metrics[agent_id]

        try:
            # Update status
            metrics.status = AgentStatus.INITIALIZING

            # Create and start agent task
            task = asyncio.create_task(self._run_agent_with_lifecycle(agent_id))
            self.agent_tasks[agent_id] = task

            # Wait a moment for initialization
            await asyncio.sleep(0.1)

            # Check if task is still running (basic health check)
            if not task.done():
                metrics.status = AgentStatus.RUNNING
                logger.info(f"[LifecycleManager] Agent started: {agent_id}")
                return True
            else:
                # Task failed immediately
                exception = task.exception()
                error_msg = str(exception) if exception else "Task failed immediately"
                metrics.update_health(False, error_msg)
                logger.error(f"[LifecycleManager] Agent failed to start: {agent_id} - {error_msg}")
                return False

        except Exception as e:
            metrics.update_health(False, str(e))
            logger.error(f"[LifecycleManager] Error starting agent {agent_id}: {e}")
            return False

    async def _stop_agent_task(self, agent_id: str):
        """Stop a specific agent's task."""
        if agent_id not in self.agent_tasks:
            return

        task = self.agent_tasks[agent_id]

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Clean up
        del self.agent_tasks[agent_id]

        # Update metrics
        metrics = self.health_metrics[agent_id]
        metrics.status = AgentStatus.STOPPED

        logger.info(f"[LifecycleManager] Agent task stopped: {agent_id}")

    async def _run_agent_with_lifecycle(self, agent_id: str):
        """
        Run an agent with lifecycle management.

        Handles automatic restarts and error recovery.
        """
        agent = self.agents[agent_id]
        metrics = self.health_metrics[agent_id]

        restart_attempts = 0

        while restart_attempts <= self.config.max_restart_attempts:
            try:
                # Reset metrics for this run
                start_time = time.time()
                metrics.status = AgentStatus.RUNNING
                metrics.consecutive_failures = 0

                # Run the agent
                await agent.run()

                # If we reach here, agent stopped gracefully
                metrics.uptime_seconds += time.time() - start_time
                metrics.status = AgentStatus.STOPPED
                break

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[LifecycleManager] Agent {agent_id} failed: {error_msg}")

                # Update metrics
                metrics.update_health(False, error_msg)
                metrics.uptime_seconds += time.time() - start_time

                # Notify callback
                if self.on_agent_failure:
                    await self.on_agent_failure(agent_id, error_msg)

                # Check if we should restart
                if (self.config.auto_restart_enabled and
                    restart_attempts < self.config.max_restart_attempts):

                    restart_attempts += 1
                    metrics.status = AgentStatus.RESTARTING
                    metrics.total_restarts += 1

                    logger.info(f"[LifecycleManager] Restarting agent {agent_id} "
                              f"(attempt {restart_attempts}/{self.config.max_restart_attempts})")

                    if self.on_agent_restart:
                        await self.on_agent_restart(agent_id)

                    # Wait before restart
                    await asyncio.sleep(self.config.restart_delay_seconds)
                else:
                    # Give up
                    metrics.status = AgentStatus.FAILED
                    logger.error(f"[LifecycleManager] Agent {agent_id} failed permanently "
                               f"after {restart_attempts} restart attempts")
                    break

    async def _health_monitor_loop(self):
        """Continuous health monitoring loop."""
        logger.info("[LifecycleManager] Health monitoring started")

        try:
            while self.running:
                await asyncio.sleep(self.config.health_check_interval)

                # Perform health checks
                await self._perform_health_checks()

                # Update system health
                system_health = await self.get_system_health()
                overall_status = system_health["overall_status"]

                # Notify if system health changed
                if self.on_system_health_change:
                    await self.on_system_health_change(overall_status)

        except asyncio.CancelledError:
            logger.info("[LifecycleManager] Health monitoring stopped")
            raise

    async def _perform_health_checks(self):
        """Perform health checks on all agents."""
        for agent_id, agent in self.agents.items():
            metrics = self.health_metrics[agent_id]

            try:
                # Check if agent is healthy
                is_healthy = agent.is_healthy()

                # Additional checks
                task_running = agent_id in self.agent_tasks and not self.agent_tasks[agent_id].done()

                # Agent is healthy if both conditions met
                overall_healthy = is_healthy and task_running

                # Update metrics
                metrics.update_health(overall_healthy)

                # Log status changes
                if metrics.status == AgentStatus.UNHEALTHY:
                    logger.warning(f"[LifecycleManager] Agent unhealthy: {agent_id} "
                                 f"(failures: {metrics.consecutive_failures})")

            except Exception as e:
                logger.error(f"[LifecycleManager] Health check failed for {agent_id}: {e}")
                metrics.update_health(False, str(e))

    def set_failure_callback(self, callback: Callable[[str, str], None]):
        """Set callback for agent failures."""
        self.on_agent_failure = callback

    def set_restart_callback(self, callback: Callable[[str], None]):
        """Set callback for agent restarts."""
        self.on_agent_restart = callback

    def set_health_change_callback(self, callback: Callable[[str], None]):
        """Set callback for system health changes."""
        self.on_system_health_change = callback
