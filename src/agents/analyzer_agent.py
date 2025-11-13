# src/agents/analyzer_agent.py
"""
Analyzer Agent: Performance metrics, health monitoring, and bottleneck detection.
Phase 2: Real-time system analysis, performance tracking, and optimization recommendations.
Integrates with all agents for comprehensive monitoring and bottleneck identification.
"""

import asyncio
import logging
import time
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import threading

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.tools.alerts import get_haiku_alerts

logger = logging.getLogger(__name__)


class AnalyzerAgent(BaseAgent):
    def __init__(self, agent_id: str, message_bus, session_logger, config: Dict[str, Any], action_executor=None):
        super().__init__(agent_id, message_bus, session_logger, config)
        self.action_executor = action_executor
        default_config = {
            "debug": False,
            "metrics_interval": 30,  # Seconds between metric collection
            "health_check_interval": 60,  # Seconds between health checks
            "bottleneck_threshold": 0.8,  # CPU/Memory threshold for alerts
            "max_metrics_history": 100,  # Number of metric snapshots to keep
            "alert_cpu_threshold": 90.0,  # CPU usage alert threshold
            "alert_memory_threshold": 85.0,  # Memory usage alert threshold
        }
        self.config = {**default_config, **(config or {})}

        # Performance monitoring data
        self.metrics_history: List[Dict[str, Any]] = []
        self.agent_performance: Dict[str, Dict[str, Any]] = {}
        self.system_health: Dict[str, Any] = {}
        self.bottlenecks: List[Dict[str, Any]] = []

        # Monitoring threads
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_active = False

        # Initialize haiku alerts
        self.alerts = get_haiku_alerts(self.message_bus)

        logger.info(f"[{self.agent_id}] Analyzer agent initialized - Performance monitoring & bottleneck detection")

    async def _trigger_bottleneck_alert(self, bottleneck: Dict[str, Any]):
        """Trigger haiku alert for system bottleneck."""
        try:
            alert_message = Message(
                from_agent=self.agent_id,
                to_agent="alerts",
                message_type="system_alert",
                content={
                    "alert_type": "bottleneck",
                    "bottleneck": bottleneck,
                    "task_name": f"System {bottleneck['type']} Monitor",
                    "task_type": "monitoring",
                    "task_id": f"bottleneck_{bottleneck['type']}_{int(time.time())}",
                },
                priority=MessagePriority.HIGH,
            )
            await self.message_bus.send(alert_message)
        except Exception as e:
            logger.error(f"Failed to trigger bottleneck alert: {e}")

    async def process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """
        Process performance analysis and monitoring requests.

        Message types:
        - get_system_metrics: Get current system performance metrics
        - get_agent_performance: Get performance data for specific agents
        - analyze_bottlenecks: Identify system bottlenecks
        - get_health_status: Get overall system health status
        - start_monitoring: Start continuous performance monitoring
        - stop_monitoring: Stop continuous performance monitoring
        """
        msg_type = message.message_type

        if msg_type == "get_system_metrics":
            return await self._handle_get_system_metrics(message)
        elif msg_type == "get_agent_performance":
            return await self._handle_get_agent_performance(message)
        elif msg_type == "analyze_bottlenecks":
            return await self._handle_analyze_bottlenecks(message)
        elif msg_type == "get_health_status":
            return await self._handle_get_health_status(message)
        elif msg_type == "start_monitoring":
            return await self._handle_start_monitoring(message)
        elif msg_type == "stop_monitoring":
            return await self._handle_stop_monitoring(message)
        else:
            logger.warning(f"[{self.agent_id}] Unknown message type: {msg_type}")
            return {"status": "error", "reason": f"Unknown message type: {msg_type}"}

    async def on_start(self):
        """Initialize performance monitoring."""
        await super().on_start()
        self._start_monitoring_thread()
        await self.alerts.start_listening()
        logger.info(f"[{self.agent_id}] Performance monitoring started")

    async def on_stop(self):
        """Cleanup monitoring resources."""
        self._stop_monitoring_thread()
        await self.alerts.stop_listening()
        await super().on_stop()
        logger.info(f"[{self.agent_id}] Performance monitoring stopped")

    async def _handle_get_system_metrics(self, message: Message) -> Dict[str, Any]:
        """Handle system metrics request."""
        metrics = self._collect_system_metrics()
        return {"status": "success", "metrics": metrics, "timestamp": datetime.now().isoformat()}

    async def _handle_get_agent_performance(self, message: Message) -> Dict[str, Any]:
        """Handle agent performance request."""
        content = message.content
        agent_id = content.get("agent_id")
        if agent_id:
            performance = self.agent_performance.get(agent_id, {})
        else:
            performance = self.agent_performance

        return {"status": "success", "agent_performance": performance, "timestamp": datetime.now().isoformat()}

    async def _handle_analyze_bottlenecks(self, message: Message) -> Dict[str, Any]:
        """Handle bottleneck analysis request."""
        bottlenecks = self._analyze_system_bottlenecks()
        return {
            "status": "success",
            "bottlenecks": bottlenecks,
            "recommendations": self._generate_bottleneck_recommendations(bottlenecks),
            "timestamp": datetime.now().isoformat(),
        }

    async def _handle_get_health_status(self, message: Message) -> Dict[str, Any]:
        """Handle health status request."""
        health_status = self._assess_system_health()
        return {"status": "success", "health": health_status, "timestamp": datetime.now().isoformat()}

    async def _handle_start_monitoring(self, message: Message) -> Dict[str, Any]:
        """Handle start monitoring request."""
        if not self.monitoring_active:
            self._start_monitoring_thread()
            return {"status": "success", "message": "Monitoring started"}
        else:
            return {"status": "info", "message": "Monitoring already active"}

    async def _handle_stop_monitoring(self, message: Message) -> Dict[str, Any]:
        """Handle stop monitoring request."""
        if self.monitoring_active:
            self._stop_monitoring_thread()
            return {"status": "success", "message": "Monitoring stopped"}
        else:
            return {"status": "info", "message": "Monitoring not active"}

    def _start_monitoring_thread(self):
        """Start background monitoring thread."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info(f"[{self.agent_id}] Background monitoring thread started")

    def _stop_monitoring_thread(self):
        """Stop background monitoring thread."""
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
            logger.info(f"[{self.agent_id}] Background monitoring thread stopped")

    def _monitoring_loop(self):
        """Background monitoring loop for continuous metrics collection."""
        while self.monitoring_active:
            try:
                # Collect metrics
                metrics = self._collect_system_metrics()
                self.metrics_history.append(metrics)

                # Keep only recent history
                if len(self.metrics_history) > self.config["max_metrics_history"]:
                    self.metrics_history.pop(0)

                # Analyze for bottlenecks
                bottlenecks = self._analyze_system_bottlenecks()
                if bottlenecks:
                    self.bottlenecks = bottlenecks

                # Update system health
                self.system_health = self._assess_system_health()

                # Sleep before next collection
                time.sleep(self.config["metrics_interval"])

            except Exception as e:
                logger.error(f"[{self.agent_id}] Monitoring error: {e}")
                time.sleep(5.0)  # Brief pause on error

    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system performance metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024**3)  # GB
            memory_total = memory.total / (1024**3)  # GB

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_used = disk.used / (1024**3)  # GB
            disk_total = disk.total / (1024**3)  # GB

            # Network metrics (basic)
            network = psutil.net_io_counters()
            bytes_sent = network.bytes_sent / (1024**2)  # MB
            bytes_recv = network.bytes_recv / (1024**2)  # MB

            # Process info
            process_count = len(psutil.pids())

            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency": cpu_freq.current if cpu_freq else None,
                },
                "memory": {
                    "percent": memory_percent,
                    "used_gb": round(memory_used, 2),
                    "total_gb": round(memory_total, 2),
                },
                "disk": {"percent": disk_percent, "used_gb": round(disk_used, 2), "total_gb": round(disk_total, 2)},
                "network": {"bytes_sent_mb": round(bytes_sent, 2), "bytes_recv_mb": round(bytes_recv, 2)},
                "processes": process_count,
            }
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error collecting metrics: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _analyze_system_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Analyze current system metrics for bottlenecks.
        Returns list of detected bottlenecks.
        Triggers haiku alerts for critical issues.
        """
        bottlenecks = []

        if not self.metrics_history:
            return bottlenecks

        # Get latest metrics
        latest = self.metrics_history[-1]

        # CPU bottleneck detection
        if latest.get("cpu", {}).get("percent", 0) > self.config["alert_cpu_threshold"]:
            bottleneck = {
                "type": "cpu",
                "severity": "high" if latest["cpu"]["percent"] > 95 else "medium",
                "metric": "CPU Usage",
                "value": latest["cpu"]["percent"],
                "threshold": self.config["alert_cpu_threshold"],
                "description": f"High CPU usage: {latest['cpu']['percent']:.1f}%",
            }
            bottlenecks.append(bottleneck)

            # Trigger haiku alert for CPU bottleneck
            asyncio.create_task(self._trigger_bottleneck_alert(bottleneck))

        # Memory bottleneck detection
        if latest.get("memory", {}).get("percent", 0) > self.config["alert_memory_threshold"]:
            bottleneck = {
                "type": "memory",
                "severity": "high" if latest["memory"]["percent"] > 95 else "medium",
                "metric": "Memory Usage",
                "value": latest["memory"]["percent"],
                "threshold": self.config["alert_memory_threshold"],
                "description": f"High memory usage: {latest['memory']['percent']:.1f}%",
            }
            bottlenecks.append(bottleneck)

            # Trigger haiku alert for memory bottleneck
            asyncio.create_task(self._trigger_bottleneck_alert(bottleneck))

        # Memory bottleneck detection
        if latest.get("memory", {}).get("percent", 0) > self.config["alert_memory_threshold"]:
            bottlenecks.append(
                {
                    "type": "memory",
                    "severity": "high" if latest["memory"]["percent"] > 95 else "medium",
                    "metric": "Memory Usage",
                    "value": latest["memory"]["percent"],
                    "threshold": self.config["alert_memory_threshold"],
                    "description": f"High memory usage: {latest['memory']['percent']:.1f}%",
                }
            )

        # Disk bottleneck detection
        if latest.get("disk", {}).get("percent", 0) > 90:
            bottlenecks.append(
                {
                    "type": "disk",
                    "severity": "medium",
                    "metric": "Disk Usage",
                    "value": latest["disk"]["percent"],
                    "threshold": 90,
                    "description": f"High disk usage: {latest['disk']['percent']:.1f}%",
                }
            )

        # Process count analysis
        if latest.get("processes", 0) > 500:
            bottlenecks.append(
                {
                    "type": "processes",
                    "severity": "low",
                    "metric": "Process Count",
                    "value": latest["processes"],
                    "threshold": 500,
                    "description": f"High process count: {latest['processes']}",
                }
            )

        return bottlenecks

    def _assess_system_health(self) -> Dict[str, Any]:
        """Assess overall system health based on metrics."""
        if not self.metrics_history:
            return {"status": "unknown", "score": 0, "issues": ["No metrics available"]}

        latest = self.metrics_history[-1]
        issues = []
        score = 100

        # CPU health
        cpu_percent = latest.get("cpu", {}).get("percent", 0)
        if cpu_percent > 90:
            issues.append("Critical CPU usage")
            score -= 30
        elif cpu_percent > 70:
            issues.append("High CPU usage")
            score -= 15

        # Memory health
        memory_percent = latest.get("memory", {}).get("percent", 0)
        if memory_percent > 90:
            issues.append("Critical memory usage")
            score -= 30
        elif memory_percent > 80:
            issues.append("High memory usage")
            score -= 15

        # Disk health
        disk_percent = latest.get("disk", {}).get("percent", 0)
        if disk_percent > 95:
            issues.append("Critical disk usage")
            score -= 20
        elif disk_percent > 85:
            issues.append("High disk usage")
            score -= 10

        # Determine status
        if score >= 80:
            status = "healthy"
        elif score >= 60:
            status = "warning"
        else:
            status = "critical"

        return {"status": status, "score": max(0, score), "issues": issues, "metrics": latest}

    def _generate_bottleneck_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for identified bottlenecks."""
        recommendations = []

        for bottleneck in bottlenecks:
            if bottleneck["type"] == "cpu":
                recommendations.extend(
                    [
                        "Consider optimizing CPU-intensive processes",
                        "Check for runaway processes using high CPU",
                        "Consider upgrading CPU or adding more cores",
                        "Monitor CPU temperature and cooling",
                    ]
                )
            elif bottleneck["type"] == "memory":
                recommendations.extend(
                    [
                        "Close unnecessary applications to free memory",
                        "Check for memory leaks in running processes",
                        "Consider adding more RAM",
                        "Use memory profiling tools to identify leaks",
                    ]
                )
            elif bottleneck["type"] == "disk":
                recommendations.extend(
                    [
                        "Clean up disk space by removing unnecessary files",
                        "Check for disk fragmentation",
                        "Consider upgrading to larger or faster storage",
                        "Monitor disk health and S.M.A.R.T. status",
                    ]
                )
            elif bottleneck["type"] == "processes":
                recommendations.extend(
                    [
                        "Review running processes and terminate unnecessary ones",
                        "Check for zombie processes",
                        "Monitor for potential malware or unauthorized processes",
                    ]
                )

        return list(set(recommendations))  # Remove duplicates
