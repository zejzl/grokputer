#!/bin/bash
# Monitoring & Alerting System
# Real-time service monitoring with intelligent alerting

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}📊 Monitoring & Alerting System${NC}"
echo "==============================="

# Configuration
MONITOR_INTERVAL=60  # seconds
ALERT_THRESHOLD=3    # consecutive failures before alert
LOG_FILE="logs/monitoring_$(date +%Y%m%d).log"
ALERT_FILE="logs/alerts_$(date +%Y%m%d).log"

# Create directories
mkdir -p logs alerts

# Global variables for tracking
declare -A SERVICE_STATUS
declare -A FAILURE_COUNT
declare -A LAST_ALERT

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

# Function to send alert
send_alert() {
    local service="$1"
    local message="$2"
    local severity="${3:-WARNING}"

    local alert_time=$(date '+%Y-%m-%d %H:%M:%S')

    # Log alert
    echo "[$alert_time] [$severity] $service: $message" >> "$ALERT_FILE"

    # Color based on severity
    case "$severity" in
        "CRITICAL")
            echo -e "${RED}🚨 CRITICAL ALERT: $service - $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  WARNING: $service - $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  INFO: $service - $message${NC}"
            ;;
    esac

    # Here you could integrate with external alerting systems:
    # - Send email
    # - Send Slack notification
    # - Send SMS
    # - Trigger PagerDuty
    # - Send to monitoring service (DataDog, New Relic, etc.)
}

# Function to check service health
check_service() {
    local service_name="$1"
    local check_command="$2"
    local expected_output="$3"

    if eval "$check_command" 2>/dev/null | grep -q "$expected_output"; then
        if [ "${SERVICE_STATUS[$service_name]}" = "DOWN" ]; then
            send_alert "$service_name" "Service is back UP" "INFO"
        fi
        SERVICE_STATUS[$service_name]="UP"
        FAILURE_COUNT[$service_name]=0
        return 0
    else
        FAILURE_COUNT[$service_name]=$((FAILURE_COUNT[$service_name] + 1))

        if [ "${FAILURE_COUNT[$service_name]}" -ge "$ALERT_THRESHOLD" ]; then
            if [ "${SERVICE_STATUS[$service_name]}" != "DOWN" ]; then
                send_alert "$service_name" "Service is DOWN (failed ${FAILURE_COUNT[$service_name]} checks)" "CRITICAL"
                SERVICE_STATUS[$service_name]="DOWN"
            fi
        fi
        return 1
    fi
}

# Function to monitor Docker containers
monitor_containers() {
    log "Monitoring Docker containers..."

    # Check MCP container
    if docker ps | grep -q grokputer-mcp; then
        check_service "MCP_Container" "docker ps" "grokputer-mcp" && log "✓ MCP container running"
    else
        check_service "MCP_Container" "echo 'not running'" "running" || log "✗ MCP container not running"
    fi

    # Check Redis in container
    if docker ps | grep -q grokputer-mcp; then
        check_service "MCP_Redis" "docker exec grokputer-mcp redis-cli ping" "PONG" && log "✓ MCP Redis responding"
    fi
}

# Function to monitor system resources
monitor_system() {
    log "Monitoring system resources..."

    # CPU usage
    local cpu_usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    cpu_usage=${cpu_usage%%.*}

    if [ "$cpu_usage" -gt 90 ]; then
        send_alert "System_CPU" "High CPU usage: ${cpu_usage}%" "CRITICAL"
    elif [ "$cpu_usage" -gt 75 ]; then
        send_alert "System_CPU" "Elevated CPU usage: ${cpu_usage}%" "WARNING"
    fi

    # Memory usage
    local mem_usage
    mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$mem_usage" -gt 90 ]; then
        send_alert "System_Memory" "High memory usage: ${mem_usage}%" "CRITICAL"
    elif [ "$mem_usage" -gt 80 ]; then
        send_alert "System_Memory" "Elevated memory usage: ${mem_usage}%" "WARNING"
    fi

    # Disk usage
    local disk_usage
    disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 95 ]; then
        send_alert "System_Disk" "Critical disk usage: ${disk_usage}%" "CRITICAL"
    elif [ "$disk_usage" -gt 85 ]; then
        send_alert "System_Disk" "High disk usage: ${disk_usage}%" "WARNING"
    fi

    log "System status - CPU: ${cpu_usage}%, Memory: ${mem_usage}%, Disk: ${disk_usage}%"
}

# Function to monitor application health
monitor_application() {
    log "Monitoring application health..."

    # Check MCP server health endpoint
    if curl -f -s --max-time 5 http://localhost:8000/health > /dev/null 2>&1; then
        check_service "MCP_Server" "curl -f -s --max-time 5 http://localhost:8000/health" "ok" && log "✓ MCP server healthy"
    else
        check_service "MCP_Server" "echo 'unhealthy'" "healthy" || log "✗ MCP server unhealthy"
    fi

    # Check Redis key count
    if docker ps | grep -q grokputer-mcp; then
        local key_count
        key_count=$(docker exec grokputer-mcp redis-cli dbsize 2>/dev/null)
        if [ "$key_count" -gt 0 ]; then
            log "✓ Redis has $key_count keys"
        else
            send_alert "Redis_Data" "Redis has no keys stored" "WARNING"
        fi
    fi
}

# Function to monitor logs for errors
monitor_logs() {
    log "Monitoring logs for errors..."

    # Check for recent errors in logs
    local error_count
    error_count=$(find logs/ -name "*.log" -mtime -1 -exec grep -l "ERROR\|CRITICAL\|FATAL" {} \; | wc -l 2>/dev/null || echo "0")

    if [ "$error_count" -gt 0 ]; then
        send_alert "Application_Logs" "Found $error_count log files with errors in the last 24 hours" "WARNING"
    fi

    # Check for authentication failures
    local auth_failures
    auth_failures=$(find logs/ -name "*.log" -mtime -1 -exec grep -c "authentication\|login.*failed\|unauthorized" {} \; 2>/dev/null | paste -sd+ | bc 2>/dev/null || echo "0")

    if [ "$auth_failures" -gt 10 ]; then
        send_alert "Security_Auth" "High number of authentication failures: $auth_failures" "CRITICAL"
    elif [ "$auth_failures" -gt 5 ]; then
        send_alert "Security_Auth" "Elevated authentication failures: $auth_failures" "WARNING"
    fi
}

# Function to monitor performance metrics
monitor_performance() {
    log "Monitoring performance metrics..."

    # Check response times (if available)
    # This would integrate with application metrics

    # Check for memory leaks (simplified)
    if command -v ps &> /dev/null; then
        local python_procs
        python_procs=$(ps aux | grep python | grep -v grep | wc -l)
        if [ "$python_procs" -gt 10 ]; then
            send_alert "Performance_Processes" "High number of Python processes: $python_procs" "WARNING"
        fi
    fi

    # Check for zombie processes
    local zombie_count
    zombie_count=$(ps aux | awk '{print $8}' | grep -c "Z" 2>/dev/null || echo "0")
    if [ "$zombie_count" -gt 0 ]; then
        send_alert "System_Zombies" "Zombie processes detected: $zombie_count" "WARNING"
    fi
}

# Function to generate monitoring report
generate_report() {
    local report_file="reports/monitoring_report_$(date +%Y%m%d_%H%M%S).md"

    cat > "$report_file" << 'EOF'
# Monitoring Report

Generated on: $(date)

## Service Status
EOF

    for service in "${!SERVICE_STATUS[@]}"; do
        status="${SERVICE_STATUS[$service]}"
        failures="${FAILURE_COUNT[$service]}"
        echo "- $service: $status (failures: $failures)" >> "$report_file"
    done

    cat >> "$report_file" << 'EOF'

## Recent Alerts
EOF

    if [ -f "$ALERT_FILE" ]; then
        tail -20 "$ALERT_FILE" >> "$report_file"
    else
        echo "No alerts in the last monitoring period" >> "$report_file"
    fi

    cat >> "$report_file" << 'EOF'

## System Metrics

### CPU Usage
EOF
    top -bn1 | head -5 >> "$report_file"

    cat >> "$report_file" << 'EOF'

### Memory Usage
EOF
    free -h >> "$report_file"

    cat >> "$report_file" << 'EOF'

### Disk Usage
EOF
    df -h >> "$report_file"

    log "Monitoring report generated: $report_file"
}

# Function to run continuous monitoring
continuous_monitoring() {
    log "Starting continuous monitoring (interval: ${MONITOR_INTERVAL}s)..."
    log "Press Ctrl+C to stop"

    while true; do
        monitor_system
        monitor_containers
        monitor_application
        monitor_logs
        monitor_performance

        # Generate report every hour
        if [ $(( $(date +%M) )) -eq 0 ]; then
            generate_report
        fi

        sleep "$MONITOR_INTERVAL"
    done
}

# Function to show status
show_status() {
    echo "Current Service Status:"
    echo "======================"

    for service in "${!SERVICE_STATUS[@]}"; do
        status="${SERVICE_STATUS[$service]}"
        failures="${FAILURE_COUNT[$service]}"

        if [ "$status" = "UP" ]; then
            echo -e "${GREEN}✓ $service: $status${NC}"
        else
            echo -e "${RED}✗ $service: $status (failures: $failures)${NC}"
        fi
    done

    echo ""
    echo "Recent Alerts:"
    echo "=============="
    if [ -f "$ALERT_FILE" ]; then
        tail -5 "$ALERT_FILE" 2>/dev/null || echo "No recent alerts"
    else
        echo "No alerts file found"
    fi
}

# Initialize service tracking
init_monitoring() {
    # Initialize all known services
    SERVICE_STATUS["MCP_Container"]="UNKNOWN"
    SERVICE_STATUS["MCP_Redis"]="UNKNOWN"
    SERVICE_STATUS["MCP_Server"]="UNKNOWN"
    SERVICE_STATUS["System_CPU"]="UNKNOWN"
    SERVICE_STATUS["System_Memory"]="UNKNOWN"
    SERVICE_STATUS["System_Disk"]="UNKNOWN"

    for service in "${!SERVICE_STATUS[@]}"; do
        FAILURE_COUNT[$service]=0
    done
}

# Main execution
case "${1:-status}" in
    "start")
        init_monitoring
        continuous_monitoring ;;
    "check")
        init_monitoring
        monitor_system
        monitor_containers
        monitor_application
        monitor_logs
        monitor_performance ;;
    "status")
        show_status ;;
    "report")
        generate_report ;;
    "alerts")
        if [ -f "$ALERT_FILE" ]; then
            cat "$ALERT_FILE"
        else
            echo "No alerts file found"
        fi ;;
    "help"|"-h"|"--help")
        echo "Monitoring & Alerting System"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  start   - Start continuous monitoring"
        echo "  check   - Run one-time check of all services"
        echo "  status  - Show current service status"
        echo "  report  - Generate monitoring report"
        echo "  alerts  - Show recent alerts"
        echo "  help    - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 start    # Start continuous monitoring"
        echo "  $0 check    # Quick health check"
        echo "  $0 status   # Current status"
        ;;
    *)
        echo "Unknown command: $1"
        "$0" help
        exit 1
        ;;
esac

echo -e "${GREEN}Monitoring check completed!${NC}"