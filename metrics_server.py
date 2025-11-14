#!/usr/bin/env python3
"""
Performance Metrics Server - Exposes Grokputer metrics to Prometheus
Run: python metrics_server.py
"""

import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from db.analytics_performance_tools import get_performance_data, log_api_call, log_maf_orchestration
from typing import Dict, Any

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()

            # Get current performance data
            perf_data = get_performance_data()

            # Format as Prometheus metrics
            metrics = self._format_prometheus_metrics(perf_data)
            self.wfile.write(metrics.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

    def _format_prometheus_metrics(self, data: Dict[str, Any]) -> str:
        """Format performance data as Prometheus metrics."""
        lines = []

        # System metrics
        lines.append("# HELP cpu_usage_percent Current CPU usage percentage")
        lines.append("# TYPE cpu_usage_percent gauge")
        lines.append(f"cpu_usage_percent {data['system']['cpu_percent']}")

        lines.append("# HELP memory_usage_percent Current memory usage percentage")
        lines.append("# TYPE memory_usage_percent gauge")
        lines.append(f"memory_usage_percent {data['system']['memory_percent']}")

        lines.append("# HELP memory_used_bytes Current memory used in bytes")
        lines.append("# TYPE memory_used_bytes gauge")
        lines.append(f"memory_used_bytes {data['system']['memory_used_gb'] * 1024**3}")

        lines.append("# HELP memory_total_bytes Total memory in bytes")
        lines.append("# TYPE memory_total_bytes gauge")
        lines.append(f"memory_total_bytes {data['system']['memory_total_gb'] * 1024**3}")

        lines.append("# HELP disk_usage_percent Current disk usage percentage")
        lines.append("# TYPE disk_usage_percent gauge")
        lines.append(f"disk_usage_percent {data['system']['disk_percent']}")

        lines.append("# HELP disk_used_bytes Current disk used in bytes")
        lines.append("# TYPE disk_used_bytes gauge")
        lines.append(f"disk_used_bytes {data['system']['disk_used_gb'] * 1024**3}")

        # API metrics
        lines.append("# HELP api_calls_total Total number of API calls")
        lines.append("# TYPE api_calls_total counter")
        lines.append(f"api_calls_total {data['api']['total_calls']}")

        lines.append("# HELP api_response_time_avg_seconds Average API response time in seconds")
        lines.append("# TYPE api_response_time_avg_seconds gauge")
        lines.append(f"api_response_time_avg_seconds {data['api']['avg_response_time']}")

        # Agent-specific API calls
        for agent, calls in data['api']['calls_per_agent'].items():
            lines.append(f"# HELP agent_api_calls_total Total API calls for agent {agent}")
            lines.append("# TYPE agent_api_calls_total counter")
            lines.append(f"agent_api_calls_total{{agent=\"{agent}\"}} {calls}")

        # MAF metrics
        lines.append("# HELP maf_orchestrations_total Total number of MAF orchestrations")
        lines.append("# TYPE maf_orchestrations_total counter")
        lines.append(f"maf_orchestrations_total {data['maf']['total_maf_orchestrations']}")

        lines.append("# HELP maf_successful_orchestrations_total Total number of successful MAF orchestrations")
        lines.append("# TYPE maf_successful_orchestrations_total counter")
        lines.append(f"maf_successful_orchestrations_total {data['maf']['successful_maf_orchestrations']}")

        lines.append("# HELP maf_success_rate Current MAF success rate")
        lines.append("# TYPE maf_success_rate gauge")
        lines.append(f"maf_success_rate {data['maf']['maf_success_rate']}")

        lines.append("# HELP maf_execution_time_avg_seconds Average MAF execution time in seconds")
        lines.append("# TYPE maf_execution_time_avg_seconds gauge")
        lines.append(f"maf_execution_time_avg_seconds {data['maf']['average_maf_execution_time']}")

        # Provider distribution
        for providers, count in data['maf']['maf_provider_distribution'].items():
            lines.append(f"# HELP maf_provider_usage_total Total MAF orchestrations using {providers} providers")
            lines.append("# TYPE maf_provider_usage_total counter")
            lines.append(f"maf_provider_usage_total{{providers=\"{providers}\"}} {count}")

        # Uptime
        lines.append("# HELP grokputer_uptime_seconds Grokputer uptime in seconds")
        lines.append("# TYPE grokputer_uptime_seconds counter")
        lines.append(f"grokputer_uptime_seconds {data['uptime']}")

        return '\n'.join(lines) + '\n'

def run_metrics_server(port: int = 8001):
    """Run the metrics server on specified port."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, MetricsHandler)
    print(f"Metrics server running on port {port}")
    print(f"Metrics available at http://localhost:{port}/metrics")
    httpd.serve_forever()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8001, help='Port to run metrics server on')
    args = parser.parse_args()

    # Start metrics server in a thread
    server_thread = threading.Thread(target=run_metrics_server, args=(args.port,))
    server_thread.daemon = True
    server_thread.start()

    print(f"Performance metrics server started on port {args.port}")
    print("Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping metrics server...")