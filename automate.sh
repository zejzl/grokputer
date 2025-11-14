#!/bin/bash
# Grokputer Master Automation Suite
# Handles: build, test, deploy, optimize, monitor, backup

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging
LOG_FILE="logs/automation_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    🤖 AUTOMATION MASTER 🤖                   ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    echo -e "${BLUE}┌─ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Create logs directory
mkdir -p logs

# Function definitions
check_dependencies() {
    print_section "Checking Dependencies"
    local missing=()

    for cmd in docker python3 pip node npm; do
        if ! command -v "$cmd" &> /dev/null; then
            missing+=("$cmd")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing[*]}"
        return 1
    fi

    print_success "All dependencies available"
}

setup_environment() {
    print_section "Environment Setup"

    # Create .env if missing
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Created .env from template"
    fi

    # Install Python dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Python dependencies installed"
    fi

    # Install Node dependencies
    if [ -f "package.json" ]; then
        npm install
        print_success "Node dependencies installed"
    fi
}

run_quality_checks() {
    print_section "Code Quality Checks"

    # Python linting
    if command -v flake8 &> /dev/null; then
        flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics || true
        print_success "Python linting completed"
    fi

    # Type checking
    if command -v mypy &> /dev/null; then
        mypy src/ --ignore-missing-imports || true
        print_success "Type checking completed"
    fi

    # Format code
    if command -v black &> /dev/null; then
        black src/ --check --diff || true
        print_success "Code formatting checked"
    fi
}

run_tests() {
    print_section "Running Tests"

    # Python tests
    if [ -d "tests" ]; then
        python -m pytest tests/ -v --tb=short || true
        print_success "Python tests completed"
    fi

    # Node tests
    if [ -f "package.json" ] && grep -q '"test"' package.json; then
        npm test || true
        print_success "Node tests completed"
    fi
}

build_all() {
    print_section "Building All Components"

    # Build MCP Alpine
    if [ -f "Dockerfile.mcp-alpine" ]; then
        docker build -f Dockerfile.mcp-alpine -t grokputer-mcp-alpine:latest .
        print_success "MCP Alpine image built"
    fi

    # Build regular image
    if [ -f "Dockerfile" ]; then
        docker build -t grokputer:latest .
        print_success "Main image built"
    fi

    # Build MCP
    if [ -f "Dockerfile.mcp" ]; then
        docker build -f Dockerfile.mcp -t grokputer-mcp:latest .
        print_success "MCP image built"
    fi
}

optimize_code() {
    print_section "Code Optimization"

    # Format code
    if command -v black &> /dev/null; then
        black src/
        print_success "Code formatted with Black"
    fi

    # Sort imports
    if command -v isort &> /dev/null; then
        isort src/
        print_success "Imports sorted"
    fi

    # Remove unused imports
    if command -v autoflake &> /dev/null; then
        autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place src/
        print_success "Unused imports removed"
    fi
}

backup_data() {
    print_section "Data Backup"

    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # Backup Redis if running
    if docker ps | grep -q grokputer-mcp; then
        docker exec grokputer-mcp redis-cli --rdb /tmp/redis_backup.rdb
        docker cp grokputer-mcp:/tmp/redis_backup.rdb "$backup_dir/"
        print_success "Redis backup created"
    fi

    # Backup vault
    if [ -d "vault" ]; then
        cp -r vault "$backup_dir/"
        print_success "Vault backup created"
    fi

    # Backup logs
    if [ -d "logs" ]; then
        cp -r logs "$backup_dir/"
        print_success "Logs backup created"
    fi

    # Create archive
    tar -czf "${backup_dir}.tar.gz" -C "$backup_dir" .
    rm -rf "$backup_dir"
    print_success "Backup archive created: ${backup_dir}.tar.gz"
}

performance_analysis() {
    print_section "Performance Analysis"

    # Python profiling
    if [ -f "main.py" ]; then
        python -m cProfile -s time main.py --help > "logs/profile_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
        print_success "Performance profile generated"
    fi

    # Memory usage
    if command -v memory_profiler &> /dev/null; then
        python -m memory_profiler main.py --help > "logs/memory_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
        print_success "Memory profile generated"
    fi
}

security_check() {
    print_section "Security Analysis"

    # Check for secrets in code
    if command -v trufflehog &> /dev/null; then
        trufflehog --regex --entropy=False . || true
        print_success "Secrets scan completed"
    fi

    # Dependency vulnerabilities
    if command -v safety &> /dev/null; then
        safety check || true
        print_success "Dependency security check completed"
    fi
}

deploy_services() {
    print_section "Service Deployment"

    # Stop existing containers
    docker stop grokputer-mcp grokputer 2>/dev/null || true
    docker rm grokputer-mcp grokputer 2>/dev/null || true

    # Deploy MCP Alpine
    if docker images | grep -q grokputer-mcp-alpine; then
        docker run -d --name grokputer-mcp \
            -p 8000:8000 -p 6379:6379 \
            --env-file .env \
            -v "$(pwd)/vault:/app/vault" \
            -v "$(pwd)/logs:/app/logs" \
            grokputer-mcp-alpine:latest
        print_success "MCP Alpine deployed"
    fi
}

monitor_services() {
    print_section "Service Monitoring"

    # Check container status
    if docker ps | grep -q grokputer-mcp; then
        print_success "MCP container running"

        # Check Redis
        if docker exec grokputer-mcp redis-cli ping 2>/dev/null | grep -q PONG; then
            print_success "Redis responding"
        else
            print_error "Redis not responding"
        fi

        # Check key count
        local key_count
        key_count=$(docker exec grokputer-mcp redis-cli dbsize 2>/dev/null)
        print_success "Redis keys: $key_count"
    else
        print_warning "MCP container not running"
    fi
}

cleanup() {
    print_section "Cleanup"

    # Remove dangling images
    docker image prune -f >/dev/null 2>&1
    print_success "Dangling images removed"

    # Remove old logs
    find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null || true
    print_success "Old logs cleaned"

    # Remove temp files
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    print_success "Temp files cleaned"
}

show_help() {
    echo "Grokputer Master Automation Suite"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  all          - Run complete automation suite"
    echo "  setup        - Environment setup"
    echo "  quality      - Code quality checks"
    echo "  test         - Run tests"
    echo "  build        - Build all components"
    echo "  optimize     - Code optimization"
    echo "  backup       - Data backup"
    echo "  security     - Security analysis"
    echo "  deploy       - Deploy services"
    echo "  monitor      - Monitor services"
    echo "  cleanup      - Cleanup temp files"
    echo "  help         - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 all          # Complete automation"
    echo "  $0 build deploy # Build and deploy"
    echo "  $0 test backup  # Test and backup"
}

# Main execution
main() {
    print_header

    case "${1:-all}" in
        "all")
            log "Starting complete automation suite"
            check_dependencies
            setup_environment
            run_quality_checks
            run_tests
            build_all
            optimize_code
            backup_data
            security_check
            deploy_services
            monitor_services
            cleanup
            log "Complete automation suite finished"
            ;;
        "setup")
            check_dependencies && setup_environment ;;
        "quality")
            run_quality_checks ;;
        "test")
            run_tests ;;
        "build")
            build_all ;;
        "optimize")
            optimize_code ;;
        "backup")
            backup_data ;;
        "security")
            security_check ;;
        "deploy")
            deploy_services ;;
        "monitor")
            monitor_services ;;
        "cleanup")
            cleanup ;;
        "help"|"-h"|"--help")
            show_help ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"