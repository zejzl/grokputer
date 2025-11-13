#!/usr/bin/env python3
"""
Anomaly Detection for Grokputer Performance Monitoring
Implements statistical anomaly detection using moving averages and standard deviations.
"""

import numpy as np
import time
from collections import deque
from typing import Dict, List, Tuple, Optional
import statistics
from db.analytics_performance_tools import get_performance_data


class AnomalyDetector:
    """Statistical anomaly detection for performance metrics."""

    def __init__(self, window_size: int = 50, threshold_std: float = 2.0):
        """
        Initialize anomaly detector.

        Args:
            window_size: Number of data points to keep for moving statistics
            threshold_std: Number of standard deviations for anomaly threshold
        """
        self.window_size = window_size
        self.threshold_std = threshold_std

        # Rolling windows for each metric
        self.cpu_history = deque(maxlen=window_size)
        self.memory_history = deque(maxlen=window_size)
        self.disk_history = deque(maxlen=window_size)
        self.api_response_time_history = deque(maxlen=window_size)
        self.maf_execution_time_history = deque(maxlen=window_size)

        # Anomaly counters
        self.anomalies_detected = {"cpu": 0, "memory": 0, "disk": 0, "api_response_time": 0, "maf_execution_time": 0}

        self.last_update = time.time()

    def update_metrics(self, perf_data: Dict) -> Dict[str, bool]:
        """
        Update rolling windows with new performance data and detect anomalies.

        Args:
            perf_data: Performance data from get_performance_data()

        Returns:
            Dictionary indicating which metrics are anomalous
        """
        current_time = time.time()

        # Update rolling windows
        self.cpu_history.append(perf_data["system"]["cpu_percent"])
        self.memory_history.append(perf_data["system"]["memory_percent"])
        self.disk_history.append(perf_data["system"]["disk_percent"])
        self.api_response_time_history.append(perf_data["api"]["avg_response_time"])
        self.maf_execution_time_history.append(perf_data["maf"]["average_maf_execution_time"])

        # Detect anomalies
        anomalies = {}

        if len(self.cpu_history) >= 10:  # Need minimum data points
            anomalies["cpu"] = self._detect_anomaly(self.cpu_history, "cpu")
            anomalies["memory"] = self._detect_anomaly(self.memory_history, "memory")
            anomalies["disk"] = self._detect_anomaly(self.disk_history, "disk")
            anomalies["api_response_time"] = self._detect_anomaly(self.api_response_time_history, "api_response_time")
            anomalies["maf_execution_time"] = self._detect_anomaly(
                self.maf_execution_time_history, "maf_execution_time"
            )
        else:
            # Not enough data for anomaly detection
            anomalies = {
                metric: False for metric in ["cpu", "memory", "disk", "api_response_time", "maf_execution_time"]
            }

        self.last_update = current_time
        return anomalies

    def _detect_anomaly(self, data: deque, metric_name: str) -> bool:
        """
        Detect anomaly in a metric using statistical analysis.

        Args:
            data: Rolling window of metric values
            metric_name: Name of the metric for tracking

        Returns:
            True if anomaly detected, False otherwise
        """
        if len(data) < 3:
            return False

        try:
            # Calculate statistics
            mean = statistics.mean(data)
            stdev = statistics.stdev(data) if len(data) > 1 else 0

            if stdev == 0:
                return False

            # Get current value (most recent)
            current_value = data[-1]

            # Check if current value deviates significantly from mean
            z_score = abs(current_value - mean) / stdev

            is_anomaly = z_score > self.threshold_std

            if is_anomaly:
                self.anomalies_detected[metric_name] += 1

            return is_anomaly

        except statistics.StatisticsError:
            # Not enough data or other statistical error
            return False

    def get_anomaly_stats(self) -> Dict:
        """Get statistics about detected anomalies."""
        return {
            "total_anomalies": sum(self.anomalies_detected.values()),
            "anomalies_by_metric": dict(self.anomalies_detected),
            "window_size": self.window_size,
            "threshold_std": self.threshold_std,
            "last_update": self.last_update,
        }

    def get_metric_stats(self, metric_name: str) -> Optional[Dict]:
        """Get statistics for a specific metric."""
        metric_map = {
            "cpu": self.cpu_history,
            "memory": self.memory_history,
            "disk": self.disk_history,
            "api_response_time": self.api_response_time_history,
            "maf_execution_time": self.maf_execution_time_history,
        }

        data = metric_map.get(metric_name)
        if not data or len(data) < 2:
            return None

        try:
            return {
                "count": len(data),
                "mean": statistics.mean(data),
                "median": statistics.median(data),
                "stdev": statistics.stdev(data),
                "min": min(data),
                "max": max(data),
                "current": data[-1],
                "anomalies_detected": self.anomalies_detected[metric_name],
            }
        except statistics.StatisticsError:
            return None


def detect_performance_anomalies() -> Dict:
    """
    Main function to detect anomalies in current performance data.

    Returns:
        Dictionary with anomaly detection results
    """
    # Get current performance data
    perf_data = get_performance_data()

    # Initialize detector (this would normally be a singleton/global instance)
    detector = AnomalyDetector()

    # Update and detect anomalies
    anomalies = detector.update_metrics(perf_data)

    # Get additional stats
    anomaly_stats = detector.get_anomaly_stats()

    result = {
        "timestamp": time.time(),
        "anomalies": anomalies,
        "anomaly_stats": anomaly_stats,
        "performance_data": perf_data,
        "recommendations": [],
    }

    # Generate recommendations based on anomalies
    if anomalies.get("cpu", False):
        result["recommendations"].append("High CPU usage detected - consider optimizing compute-intensive operations")

    if anomalies.get("memory", False):
        result["recommendations"].append(
            "High memory usage detected - check for memory leaks or increase system memory"
        )

    if anomalies.get("disk", False):
        result["recommendations"].append("High disk usage detected - clean up old logs and backups")

    if anomalies.get("api_response_time", False):
        result["recommendations"].append(
            "Slow API response times detected - investigate network or backend performance issues"
        )

    if anomalies.get("maf_execution_time", False):
        result["recommendations"].append(
            "Slow MAF execution detected - review orchestration logic and provider selection"
        )

    return result


# Global anomaly detector instance
_anomaly_detector = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create global anomaly detector instance."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector


def update_anomaly_detection():
    """Update anomaly detection with current performance data."""
    detector = get_anomaly_detector()
    perf_data = get_performance_data()
    return detector.update_metrics(perf_data)


if __name__ == "__main__":
    # Test anomaly detection
    result = detect_performance_anomalies()
    print("Anomaly Detection Results:")
    print(f"Anomalies: {result['anomalies']}")
    print(f"Total Anomalies: {result['anomaly_stats']['total_anomalies']}")
    print(f"Recommendations: {result['recommendations']}")
