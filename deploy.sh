#!/bin/bash
# Deployment Orchestration Tool
# Intelligent multi-environment deployment management

set -e

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
    deploy_log "Rolling back deployment..."

    if [ ! -d "$BACKUP_DIR" ]; then
        deploy_log "No rollback point found!"
        return 1
    fi

    # Stop current services
    docker stop grokputer-mcp 2>/dev/null || true
    docker rm grokputer-mcp 2>/dev/null || true

    # Restore from backup
    if [ -f "$BACKUP_DIR/redis_rollback.rdb" ]; then
        deploy_log "Restoring Redis data..."
        # This would need to be implemented based on your Redis setup
    fi

    if [ -f "$BACKUP_DIR/.env" ]; then
        deploy_log "Restoring configuration..."
        cp "$BACKUP_DIR/.env" .env
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
    available_space=$(df / | tail -1 | awk '{print $4}')
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
    local image_tag="${2:-latest}"

    deploy_log "Deploying to $environment environment..."

    # Environment-specific configuration
    case "$environment" in
        "staging")
            local container_name="grokputer-mcp-staging"
            local ports="8001:8000 6380:6379"
            ;;
        "production")
            local container_name="grokputer-mcp"
            local ports="8000:8000 6379:6379"
            ;;
        "development")
            local container_name="grokputer-mcp-dev"
            local ports="8002:8000 6381:6379"
            ;;
        *)
            deploy_log "Unknown environment: $environment"
            return 1
            ;;
    esac

    # Stop existing container
    docker stop "$container_name" 2>/dev/null || true
    docker rm "$container_name" 2>/dev/null || true

    # Start new container
    docker run -d \
        --name "$container_name" \
        -p "$ports" \
        --env-file .env \
        -v "$(pwd)/vault:/app/vault" \
        -v "$(pwd)/logs:/app/logs" \
        "grokputer-mcp-alpine:$image_tag"

    deploy_log "Container $container_name deployed on ports $ports"
}

# Function to run health checks
run_health_checks() {
    local environment="$1"
    local max_attempts=30
    local attempt=1

    deploy_log "Running health checks for $environment..."

    while [ $attempt -le $max_attempts ]; do
        deploy_log "Health check attempt $attempt/$max_attempts..."

        # Check container
        if ! docker ps | grep -q "grokputer-mcp"; then
            deploy_log "Container not running"
            sleep 5
            ((attempt++))
            continue
        fi

        # Check Redis
        if ! docker exec grokputer-mcp redis-cli ping 2>/dev/null | grep -q PONG; then
            deploy_log "Redis not responding"
            sleep 5
            ((attempt++))
            continue
        fi

        # Check application
        if curl -f -s --max-time 10 "http://localhost:8000/health" > /dev/null 2>&1; then
            deploy_log "All health checks passed!"
            return 0
        else
            deploy_log "Application health check failed"
            sleep 5
            ((attempt++))
            continue
        fi
    done

    deploy_log "Health checks failed after $max_attempts attempts"
    return 1
}

# Function to run smoke tests
run_smoke_tests() {
    deploy_log "Running smoke tests..."

    # Basic connectivity test
    if ! curl -f -s --max-time 5 "http://localhost:8000" > /dev/null; then
        deploy_log "Basic connectivity test failed"
        return 1
    fi

    # Redis connectivity test
    if ! docker exec grokputer-mcp redis-cli ping | grep -q PONG; then
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

    # Clean up dangling images
    docker image prune -f >/dev/null 2>&1

    deploy_log "Cleanup completed"
}

# Function to deploy to staging
deploy_staging() {
    deploy_log "Starting staging deployment..."

    create_rollback
    validate_prerequisites
    build_artifacts "staging"
    deploy_to_environment "staging"

    if run_health_checks "staging" && run_smoke_tests; then
        notify_stakeholders "staging" "success"
        deploy_log "Staging deployment completed successfully"
    else
        deploy_log "Staging deployment failed, rolling back..."
        rollback_deployment
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

    if run_health_checks "production" && run_smoke_tests; then
        # Additional production validation
        local key_count
        key_count=$(docker exec grokputer-mcp redis-cli dbsize 2>/dev/null)
        if [ "$key_count" -lt 10 ]; then
            deploy_log "Warning: Low Redis key count in production: $key_count"
        fi

        notify_stakeholders "production" "success"
        cleanup_deployment
        deploy_log "Production deployment completed successfully"
    else
        deploy_log "Production deployment failed, rolling back..."
        rollback_deployment
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
        rollback_deployment ;;
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
        echo "  rollback   - Rollback last deployment"
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