#!/bin/bash
# Grokputer Redis Alpine MCP Auto-Setup Script
# Automates: build, env setup, container launch, Redis key import

set -e  # Exit on any error

echo "🚀 Grokputer Redis Alpine MCP Auto-Setup"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is not installed. Please install Python3 first."
        exit 1
    fi

    print_success "Prerequisites check passed"
}

# Setup environment
setup_environment() {
    print_status "Setting up environment..."

    # Copy .env.example to .env if it doesn't exist
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env from .env.example"
            print_warning "Please edit .env with your actual API keys before running!"
        else
            print_error ".env.example not found"
            exit 1
        fi
    else
        print_success ".env already exists"
    fi
}

# Build Docker image
build_image() {
    print_status "Building Grokputer MCP Alpine image..."

    if docker build -f Dockerfile.mcp-alpine -t grokputer-mcp-alpine:latest .; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Start container
start_container() {
    print_status "Starting container..."

    # Stop and remove existing container if it exists
    docker stop grokputer-mcp 2>/dev/null || true
    docker rm grokputer-mcp 2>/dev/null || true

    # Start new container
    if docker run -d \
        --name grokputer-mcp \
        -p 8000:8000 \
        -p 6379:6379 \
        --env-file .env \
        -v "$(pwd)/vault:/app/vault" \
        -v "$(pwd)/logs:/app/logs" \
        grokputer-mcp-alpine:latest; then

        print_success "Container started successfully"
        print_status "Waiting for services to initialize..."
        sleep 5
    else
        print_error "Failed to start container"
        exit 1
    fi
}

# Import Redis keys
import_redis_keys() {
    print_status "Importing Redis keys..."

    if [ -f "vault/redis_backup.json" ]; then
        # Create a temporary script to automate the restore
        cat > /tmp/redis_restore_auto.py << 'EOF'
import redis
import json
import os
import sys

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
BACKUP_FILE = './vault/redis_backup.json'

def restore_redis():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        r.ping()
        
        with open(BACKUP_FILE, 'r') as f:
            full_backup = json.load(f)
        
        data = full_backup.get('data', {})
        restored_count = 0
        errors = []
        
        for key, value in data.items():
            try:
                if isinstance(value, dict) and 'error' not in value:
                    r.hset(key, mapping=value)
                elif isinstance(value, list):
                    r.rpush(key, *value)
                elif value is not None:
                    r.set(key, value)
                else:
                    errors.append(f"Skipped {key}: Unknown type")
                    continue
                
                restored_count += 1
                
            except Exception as e:
                errors.append(f"Error restoring {key}: {e}")
        
        print(f"Redis restore complete: {restored_count} keys restored from {full_backup.get('total_keys', 0)} total.")
        if errors:
            print("Errors:", len(errors))
        return True
        
    except Exception as e:
        print(f"Restore failed: {e}")
        return False

if __name__ == '__main__':
    if restore_redis():
        sys.exit(0)
    else:
        sys.exit(1)
EOF

        # Copy and run the restore script in container
        docker cp /tmp/redis_restore_auto.py grokputer-mcp:/app/restore_auto.py
        docker cp vault/redis_backup.json grokputer-mcp:/app/vault/

        if docker exec grokputer-mcp python3 restore_auto.py; then
            print_success "Redis keys imported successfully"
        else
            print_error "Failed to import Redis keys"
            exit 1
        fi

        # Cleanup
        rm -f /tmp/redis_restore_auto.py
    else
        print_warning "No Redis backup found at vault/redis_backup.json - skipping import"
    fi
}

# Verify setup
verify_setup() {
    print_status "Verifying setup..."

    # Check if container is running
    if ! docker ps | grep -q grokputer-mcp; then
        print_error "Container is not running"
        exit 1
    fi

    # Check MCP server health
    if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "MCP server is healthy"
    else
        print_warning "MCP server health check failed (may not have health endpoint)"
    fi

    # Check Redis connection
    if docker exec grokputer-mcp redis-cli ping | grep -q PONG; then
        print_success "Redis is responding"
    else
        print_error "Redis is not responding"
        exit 1
    fi

    # Check Redis key count
    KEY_COUNT=$(docker exec grokputer-mcp redis-cli dbsize)
    if [ "$KEY_COUNT" -gt 0 ]; then
        print_success "Redis has $KEY_COUNT keys loaded"
    else
        print_warning "Redis has no keys loaded"
    fi
}

# Show usage info
show_info() {
    echo ""
    print_success "Setup complete! 🎉"
    echo ""
    echo "Services running:"
    echo "  • MCP Server: http://localhost:8000"
    echo "  • Redis: localhost:6379"
    echo ""
    echo "Container name: grokputer-mcp"
    echo ""
    echo "To stop: docker stop grokputer-mcp"
    echo "To restart: docker start grokputer-mcp"
    echo "To view logs: docker logs grokputer-mcp"
    echo "To shell: docker exec -it grokputer-mcp sh"
    echo ""
    echo "Don't forget to add your API keys to .env file!"
}

# Main execution
main() {
    check_prerequisites
    setup_environment
    build_image
    start_container
    import_redis_keys
    verify_setup
    show_info
}

# Run main function
main "$@"