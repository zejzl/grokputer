#!/bin/bash
# Deployment Orchestration Tool
# Intelligent multi-environment deployment management

set -e

# Git Bash/MSYS rewrites POSIX-looking paths passed to docker.exe (it mangles
# -v /d/x:/app/vault), so turn that off and hand docker a native host path.
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
        export MSYS_NO_PATHCONV=1
        HOST_DIR="$(pwd -W)"
        ;;
    *)
        HOST_DIR="$(pwd)"
        ;;
esac

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}🚀 Deployment Orchestration Tool${NC}"
echo "==============================="

# Configuration
DEPLOY_LOG="logs/deployment_$(date +%Y%m%d_%H%M%S).log"
BACKUP_DIR="backups/pre_deploy_$(date +%Y%m%d_%H%M%S)"

# Function to log deployment steps
deploy_log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [DEPLOY] $*" | tee -a "$DEPLOY_LOG"
}

# Per-environment container name and host ports. Every check below goes through
# these, so a staging deploy never inspects or removes the production container.
env_container() {
    case "$1" in
        staging) echo "grokputer-mcp-staging" ;;
        production) echo "grokputer-mcp" ;;
        development) echo "grokputer-mcp-dev" ;;
        *) return 1 ;;
    esac
}

env_mcp_port() {
    case "$1" in
        staging) echo 8001 ;;
        production) echo 8000 ;;
        development) echo 8002 ;;
    esac
}

env_redis_port() {
    case "$1" in
        staging) echo 6380 ;;
        production) echo 6379 ;;
        development) echo 6381 ;;
    esac
}

# Function to create rollback point
create_rollback() {
    deploy_log "Creating rollback point..."

    mkdir -p "$BACKUP_DIR"

    # Backup current state
    if docker ps | grep -q grokputer-mcp; then
        deploy_log "Backing up running containers..."
        docker exec grokputer-mcp redis-cli --rdb /tmp/redis_rollback.rdb 2>/dev/null || true
        docker cp grokputer-mcp:/tmp/redis_rollback.rdb "$BACKUP_DIR/" 2>/dev/null || true
    fi

    # Backup configuration
    cp -r vault "$BACKUP_DIR/" 2>/dev/null || true
    cp .env "$BACKUP_DIR/" 2>/dev/null || true

    deploy_log "Rollback point created: $BACKUP_DIR"
}

# Function to rollback deployment
rollback_deployment() {
    local environment="${1:-production}"
    local container_name
    container_name=$(env_container "$environment") || { deploy_log "Unknown environment: $environment"; return 1; }

    deploy_log "Rolling back $environment deployment..."

    # A standalone 'rollback' run has a fresh timestamp, so fall back to the newest rollback point
    local backup_dir="$BACKUP_DIR"
    if [ ! -d "$backup_dir" ]; then
        backup_dir=$(ls -d backups/pre_deploy_* 2>/dev/null | tail -1)
    fi
    if [ -z "$backup_dir" ] || [ ! -d "$backup_dir" ]; then
        deploy_log "No rollback point found!"
        return 1
    fi
    deploy_log "Using rollback point: $backup_dir"

    # Stop only this environment's container
    docker stop "$container_name" 2>/dev/null || true
    docker rm "$container_name" 2>/dev/null || true

    # Restore from backup
    if [ -f "$backup_dir/redis_rollback.rdb" ]; then
        deploy_log "Redis snapshot kept at $backup_dir/redis_rollback.rdb (restoring it is not automated)"
    fi

    if [ -f "$backup_dir/.env" ]; then
        deploy_log "Restoring configuration..."
        cp "$backup_dir/.env" .env
    fi

    deploy_log "Rollback completed"
}

# Function to validate deployment prerequisites
validate_prerequisites() {
    deploy_log "Validating deployment prerequisites..."

    # Check Docker
    if ! docker --version &> /dev/null; then
        deploy_log "Docker not available"
        return 1
    fi

    # Check environment file
    if [ ! -f ".env" ]; then
        deploy_log "Environment file .env not found"
        return 1
    fi

    # Check required environment variables
    if ! grep -q "XAI_API_KEY" .env; then
        deploy_log "XAI_API_KEY not found in .env"
        return 1
    fi

    # Check disk space
    local available_space
    available_space=$(df -P . | tail -1 | awk '{print $4}')
    if [ "$available_space" -lt 1000000 ]; then  # Less than ~1GB
        deploy_log "Insufficient disk space: ${available_space}KB available"
        return 1
    fi

    deploy_log "Prerequisites validation passed"
}

# Function to build artifacts
build_artifacts() {
    local environment="$1"

    deploy_log "Building artifacts for $environment..."

    # Build Docker images
    if [ -f "Dockerfile.mcp-alpine" ]; then
        docker build -f Dockerfile.mcp-alpine -t "grokputer-mcp-alpine:$environment" .
        docker tag "grokputer-mcp-alpine:$environment" "grokputer-mcp-alpine:latest"
        deploy_log "MCP Alpine image built"
    fi

    # Run tests
    deploy_log "Running tests..."
    if [ -f "automate.sh" ]; then
        ./automate.sh test
    fi

    # Run security checks
    deploy_log "Running security checks..."
    if [ -f "manage-dependencies.sh" ]; then
        ./manage-dependencies.sh check
    fi
}

# Function to deploy to environment
deploy_to_environment() {
    local environment="$1"
    local image_tag="${2:-$environment}"
    local container_name mcp_port redis_port

    deploy_log "Deploying to $environment environment..."

    container_name=$(env_container "$environment") || { deploy_log "Unknown environment: $environment"; return 1; }
    mcp_port=$(env_mcp_port "$environment")
    redis_port=$(env_redis_port "$environment")

    # Stop existing container
    docker stop "$container_name" 2>/dev/null || true
    docker rm "$container_name" 2>/dev/null || true

    # Start new container
    docker run -d \
        --name "$container_name" \
        -p "$mcp_port:8000" \
        -p "$redis_port:6379" \
        --env-file .env \
        -v "$HOST_DIR/vault:/app/vault" \
        -v "$HOST_DIR/logs:/app/logs" \
        "grokputer-mcp-alpine:$image_tag"

    deploy_log "Container $container_name deployed (MCP :$mcp_port, Redis :$redis_port)"
}

# Function to run health checks
run_health_checks() {
    local environment="$1"
    local container_name mcp_port
    container_name=$(env_container "$environment") || return 1
    mcp_port=$(env_mcp_port "$environment")
    local max_attempts=30
    local attempt=1

    deploy_log "Running health checks for $environment ($container_name)..."

    while [ $attempt -le $max_attempts ]; do
        deploy_log "Health check attempt $attempt/$max_attempts..."

        # Check container
        if ! docker ps --format '{{.Names}}' | grep -qx "$container_name"; then
            deploy_log "Container not running"
            sleep 5
            attempt=$((attempt + 1))
            continue
        fi

        # Check Redis
        if ! docker exec "$container_name" redis-cli ping 2>/dev/null | grep -q PONG; then
            deploy_log "Redis not responding"
            sleep 5
            attempt=$((attempt + 1))
            continue
        fi

        # Check application: the server has no /health route, any HTTP status from /mcp means it is serving
        local status
        status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://localhost:$mcp_port/mcp" 2>/dev/null)
        if [ -n "$status" ] && [ "$status" != "000" ]; then
            deploy_log "All health checks passed! (HTTP $status from /mcp)"
            return 0
        else
            deploy_log "Application health check failed"
            sleep 5
            attempt=$((attempt + 1))
            continue
        fi
    done

    deploy_log "Health checks failed after $max_attempts attempts"
    return 1
}

# Function to run smoke tests
run_smoke_tests() {
    local environment="$1"
    local container_name mcp_port status
    container_name=$(env_container "$environment") || return 1
    mcp_port=$(env_mcp_port "$environment")

    deploy_log "Running smoke tests..."

    # Basic connectivity test
    status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:$mcp_port/mcp" 2>/dev/null)
    if [ -z "$status" ] || [ "$status" = "000" ]; then
        deploy_log "Basic connectivity test failed"
        return 1
    fi

    # Redis connectivity test
    if ! docker exec "$container_name" redis-cli ping | grep -q PONG; then
        deploy_log "Redis connectivity test failed"
        return 1
    fi

    deploy_log "Smoke tests passed"
}

# Function to notify stakeholders
notify_stakeholders() {
    local environment="$1"
    local status="$2"

    deploy_log "Notifying stakeholders of $status deployment to $environment..."

    # This would integrate with your notification system
    # Examples:
    # - Send email
    # - Send Slack message
    # - Send Teams notification
    # - Update status page
    # - Send SMS alerts

    case "$status" in
        "success")
            deploy_log "✅ Deployment to $environment completed successfully"
            # Send success notification
            ;;
        "failure")
            deploy_log "❌ Deployment to $environment failed"
            # Send failure alert
            ;;
        "rollback")
            deploy_log "🔄 Deployment rolled back"
            # Send rollback notification
            ;;
    esac
}

# Function to cleanup after deployment
cleanup_deployment() {
    deploy_log "Cleaning up deployment artifacts..."

    # Remove old images (keep last 3)
    docker images grokputer-mcp-alpine --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}" | tail -n +2 | head -n -3 | awk '{print $3}' | xargs -r docker rmi 2>/dev/null || true

    deploy_log "Cleanup completed"
}

# Function to deploy to staging
deploy_staging() {
    deploy_log "Starting staging deployment..."

    create_rollback
    validate_prerequisites
    build_artifacts "staging"
    deploy_to_environment "staging"

    if run_health_checks "staging" && run_smoke_tests "staging"; then
        notify_stakeholders "staging" "success"
        deploy_log "Staging deployment completed successfully"
    else
        deploy_log "Staging deployment failed, rolling back..."
        rollback_deployment "staging"
        notify_stakeholders "staging" "failure"
        return 1
    fi
}

# Function to deploy to production
deploy_production() {
    deploy_log "Starting production deployment..."

    # Additional production checks
    if [ ! -f "vault/redis_backup.json" ]; then
        deploy_log "Production deployment requires Redis backup"
        return 1
    fi

    create_rollback
    validate_prerequisites
    build_artifacts "production"
    deploy_to_environment "production"

    if run_health_checks "production" && run_smoke_tests "production"; then
        # Additional production validation
        local key_count
        key_count=$(docker exec "$(env_container production)" redis-cli dbsize 2>/dev/null)
        if [ "$key_count" -lt 10 ]; then
            deploy_log "Warning: Low Redis key count in production: $key_count"
        fi

        notify_stakeholders "production" "success"
        cleanup_deployment
        deploy_log "Production deployment completed successfully"
    else
        deploy_log "Production deployment failed, rolling back..."
        rollback_deployment "production"
        notify_stakeholders "production" "failure"
        return 1
    fi
}

# Function to show deployment status
show_deployment_status() {
    echo "Deployment Status:"
    echo "=================="

    echo "Running Containers:"
    docker ps --filter "name=grokputer" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    echo "Available Images:"
    docker images grokputer* --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

    echo ""
    echo "Recent Deployments:"
    ls -la logs/deployment_* 2>/dev/null | head -5 || echo "No deployment logs found"
}

# Main execution
case "${1:-status}" in
    "staging")
        deploy_staging ;;
    "production")
        deploy_production ;;
    "rollback")
        rollback_deployment "${2:-production}" ;;
    "status")
        show_deployment_status ;;
    "validate")
        validate_prerequisites ;;
    "cleanup")
        cleanup_deployment ;;
    "help"|"-h"|"--help")
        echo "Deployment Orchestration Tool"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  staging    - Deploy to staging environment"
        echo "  production - Deploy to production environment"
        echo "  rollback   - Rollback last deployment: rollback [staging|production]"
        echo "  status     - Show deployment status"
        echo "  validate   - Validate deployment prerequisites"
        echo "  cleanup    - Clean up deployment artifacts"
        echo "  help       - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 staging     # Deploy to staging"
        echo "  $0 production  # Deploy to production"
        echo "  $0 rollback    # Rollback deployment"
        ;;
    *)
        echo "Unknown command: $1"
        "$0" help
        exit 1
        ;;
esac

deploy_log "Deployment orchestration completed"