#!/bin/bash
# Documentation Automation Tool
# Auto-generate and maintain project documentation

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}📚 Documentation Automation Tool${NC}"
echo "================================="

# Create docs directory
mkdir -p docs

# Function to generate API documentation
generate_api_docs() {
    echo -e "${BLUE}Generating API documentation...${NC}"

    if [ -f "grokputer_server.py" ]; then
        # Extract FastMCP tool definitions
        echo "# Grokputer MCP API Documentation" > docs/api.md
        echo "" >> docs/api.md
        echo "Generated on: $(date)" >> docs/api.md
        echo "" >> docs/api.md

        # Extract tool definitions
        grep -A 5 "@mcp.tool()" grokputer_server.py | while read -r line; do
            if [[ $line == @mcp.tool()* ]]; then
                # Found a tool definition
                read -r func_line
                if [[ $func_line == async\ def* ]]; then
                    func_name=$(echo "$func_line" | sed 's/async def \([^(]*\).*/\1/')
                    echo "## $func_name" >> docs/api.md
                    echo "" >> docs/api.md

                    # Extract docstring
                    grep -A 10 -B 2 "$func_name" grokputer_server.py | grep '"""' | head -2 | sed 's/"""//g' | sed 's/^\s*//g' >> docs/api.md
                    echo "" >> docs/api.md
                fi
            fi
        done

        echo -e "${GREEN}✓ API documentation generated${NC}"
    fi
}

# Function to generate code documentation
generate_code_docs() {
    echo -e "${BLUE}Generating code documentation...${NC}"

    if command -v pdoc &> /dev/null; then
        echo "Generating Python documentation..."
        pdoc --html --output-dir docs/code src/ 2>/dev/null || true
        echo -e "${GREEN}✓ Code documentation generated${NC}"
    fi

    # Generate module overview
    echo "# Codebase Overview" > docs/codebase.md
    echo "" >> docs/codebase.md
    echo "Generated on: $(date)" >> docs/codebase.md
    echo "" >> docs/codebase.md

    echo "## Directory Structure" >> docs/codebase.md
    echo "\`\`\`" >> docs/codebase.md
    find src/ -type f -name "*.py" | head -20 >> docs/codebase.md
    echo "\`\`\`" >> docs/codebase.md

    echo "" >> docs/codebase.md
    echo "## Module Summary" >> docs/codebase.md
    echo "" >> docs/codebase.md

    for file in src/**/*.py; do
        if [ -f "$file" ]; then
            lines=$(wc -l < "$file")
            classes=$(grep -c "^class " "$file")
            functions=$(grep -c "^def " "$file")
            echo "- **${file#src/}**: $lines lines, $classes classes, $functions functions" >> docs/codebase.md
        fi
    done
}

# Function to generate deployment documentation
generate_deployment_docs() {
    echo -e "${BLUE}Generating deployment documentation...${NC}"

    cat > docs/deployment.md << 'EOF'
# Deployment Guide

## Prerequisites

- Docker 20.10+
- Python 3.11+
- 2GB RAM minimum
- 5GB disk space

## Quick Start

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd grokputer

# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Run automated setup
./automate.sh all
```

### Production Deployment
```bash
# Deploy to production
./deploy.sh production

# Monitor deployment
./monitor.sh start
```

## Environment Configuration

### Required Environment Variables
- `XAI_API_KEY`: Your xAI API key
- `REDIS_URL`: Redis connection URL (default: redis://redis:6379)

### Optional Environment Variables
- `ANTHROPIC_API_KEY`: Claude API key for fallback
- `GEMINI_API_KEY`: Gemini API key for fallback
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Docker Deployment

### Single Container (Recommended)
```bash
docker run -d \
  --name grokputer-mcp \
  -p 8000:8000 -p 6379:6379 \
  --env-file .env \
  -v ./vault:/app/vault \
  grokputer-mcp-alpine:latest
```

### Docker Compose
```yaml
version: '3.8'
services:
  grokputer:
    image: grokputer-mcp-alpine:latest
    ports:
      - "8000:8000"
      - "6379:6379"
    env_file:
      - .env
    volumes:
      - ./vault:/app/vault
      - ./logs:/app/logs
```

## Service Endpoints

- **MCP Server**: http://localhost:8000
- **Redis**: localhost:6379
- **Health Check**: http://localhost:8000/health

## Monitoring

### Health Checks
```bash
# Check all services
./monitor.sh check

# Continuous monitoring
./monitor.sh start
```

### Logs
```bash
# View container logs
docker logs grokputer-mcp

# View application logs
tail -f logs/grokputer.log
```

## Backup and Recovery

### Automated Backup
```bash
./automate.sh backup
```

### Manual Backup
```bash
# Backup Redis data
docker exec grokputer-mcp redis-cli --rdb /tmp/backup.rdb
docker cp grokputer-mcp:/tmp/backup.rdb ./backups/

# Backup vault
cp -r vault ./backups/
```

### Recovery
```bash
# Restore from backup
./restore_redis.py
cp -r ./backups/vault ./
```
EOF

    echo -e "${GREEN}✓ Deployment documentation generated${NC}"
}

# Function to generate performance documentation
generate_performance_docs() {
    echo -e "${BLUE}Generating performance documentation...${NC}"

    cat > docs/performance.md << 'EOF'
# Performance Guide

## System Requirements

### Minimum Requirements
- CPU: 2 cores
- RAM: 2GB
- Disk: 5GB SSD
- Network: 10Mbps

### Recommended Requirements
- CPU: 4+ cores
- RAM: 4GB+
- Disk: 20GB SSD
- Network: 100Mbps

## Performance Optimization

### Code Optimizations
```bash
# Run performance analysis
./optimize-performance.sh all

# View performance reports
ls reports/performance_*
```

### Memory Optimization
- Use generators for large datasets
- Implement proper object cleanup
- Monitor memory usage with profiling tools

### Database Optimization
- Use Redis for session data
- Implement proper indexing
- Monitor query performance

## Monitoring Performance

### Key Metrics
- Response time < 100ms
- Memory usage < 80%
- CPU usage < 70%
- Error rate < 1%

### Monitoring Commands
```bash
# System monitoring
./monitor.sh check

# Performance profiling
python -m cProfile main.py

# Memory profiling
python -m memory_profiler main.py
```

## Scaling Considerations

### Horizontal Scaling
- Deploy multiple MCP instances
- Use load balancer
- Shared Redis backend

### Vertical Scaling
- Increase CPU cores
- Add more RAM
- Use faster storage

## Troubleshooting

### High CPU Usage
1. Check for infinite loops
2. Profile code execution
3. Optimize algorithms

### High Memory Usage
1. Check for memory leaks
2. Use memory profiling
3. Implement garbage collection

### Slow Response Times
1. Profile request handling
2. Check database queries
3. Optimize I/O operations
EOF

    echo -e "${GREEN}✓ Performance documentation generated${NC}"
}

# Function to generate troubleshooting guide
generate_troubleshooting_docs() {
    echo -e "${BLUE}Generating troubleshooting documentation...${NC}"

    cat > docs/troubleshooting.md << 'EOF'
# Troubleshooting Guide

## Common Issues

### Container Won't Start
**Symptoms:** `docker run` fails
**Solutions:**
```bash
# Check Docker status
docker --version
docker info

# Check environment file
cat .env

# Check available resources
df -h
free -h

# View detailed logs
docker logs grokputer-mcp
```

### Redis Connection Failed
**Symptoms:** Application can't connect to Redis
**Solutions:**
```bash
# Check Redis status
docker exec grokputer-mcp redis-cli ping

# Check Redis logs
docker logs grokputer-mcp | grep redis

# Verify Redis configuration
docker exec grokputer-mcp redis-cli config get *

# Restart Redis
docker exec grokputer-mcp redis-cli shutdown
```

### API Key Errors
**Symptoms:** Authentication failures
**Solutions:**
```bash
# Check environment variables
echo $XAI_API_KEY

# Verify .env file
cat .env | grep API_KEY

# Test API key
curl -H "Authorization: Bearer $XAI_API_KEY" https://api.x.ai/v1/models
```

### High Resource Usage
**Symptoms:** System slowdown, high CPU/memory
**Solutions:**
```bash
# Check system resources
top
free -h
df -h

# Monitor processes
ps aux | grep python

# Check application logs
tail -f logs/grokputer.log

# Profile performance
./optimize-performance.sh test
```

### Network Connectivity Issues
**Symptoms:** Can't access services
**Solutions:**
```bash
# Check port availability
netstat -tlnp | grep :8000
netstat -tlnp | grep :6379

# Test connectivity
curl http://localhost:8000/health
docker exec grokputer-mcp redis-cli ping

# Check firewall
sudo ufw status
sudo iptables -L
```

## Log Analysis

### Finding Errors
```bash
# Search for errors
grep ERROR logs/*.log

# Recent errors
tail -f logs/grokputer.log | grep ERROR

# Error frequency
grep ERROR logs/*.log | wc -l
```

### Performance Issues
```bash
# Slow requests
grep "duration\|time" logs/*.log | tail -10

# Memory issues
grep "memory\|Memory" logs/*.log
```

## Recovery Procedures

### Data Recovery
```bash
# Restore from backup
./restore_redis.py

# Verify data integrity
docker exec grokputer-mcp redis-cli dbsize
```

### Service Recovery
```bash
# Restart services
docker restart grokputer-mcp

# Full redeploy
./deploy.sh production
```

### System Recovery
```bash
# Free up resources
docker system prune -a
rm -rf logs/*.log.old

# Restart system services
sudo systemctl restart docker
```

## Getting Help

### Debug Information
```bash
# System information
uname -a
docker --version
python --version

# Application status
./monitor.sh status

# Recent logs
tail -50 logs/grokputer.log
```

### Support Resources
- Check existing issues on GitHub
- Review documentation in `docs/`
- Run diagnostic commands
- Provide debug information when reporting issues
EOF

    echo -e "${GREEN}✓ Troubleshooting documentation generated${NC}"
}

# Function to generate README
generate_readme() {
    echo -e "${BLUE}Generating README...${NC}"

    cat > README.md << 'EOF'
# Grokputer 🤖

**AI-powered automation and orchestration platform with MCP (Model Context Protocol) support**

## Features

- 🚀 **Full Automation Suite** - Development, testing, deployment, monitoring
- 🐳 **Containerized** - Docker-based with Alpine Linux optimization
- 📊 **Intelligent Monitoring** - Real-time health checks and alerting
- 🔒 **Security First** - Automated security scanning and updates
- 📈 **Performance Optimized** - Profiling, optimization, and scaling
- 🔄 **GitOps Ready** - Automated workflows and CI/CD integration

## Quick Start

### Automated Setup
```bash
# One-command setup
./automate.sh all

# Or Windows
automate.bat all
```

### Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Run MCP server
docker run -d -p 8000:8000 -p 6379:6379 --env-file .env grokputer-mcp-alpine
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Server    │    │     Redis       │    │     Vault       │
│   (FastAPI)     │◄──►│   (Memory)      │    │   (Storage)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┴────────────────────────┘
                          Automation Suite
```

## Available Tools

### Core Automation
- `automate.sh` - Master automation suite
- `setup-mcp-alpine.sh` - MCP container setup
- `deploy.sh` - Deployment orchestration
- `monitor.sh` - Health monitoring & alerting

### Development Tools
- `git-workflow.sh` - Smart Git operations
- `code-review.sh` - AI-powered code review
- `optimize-performance.sh` - Performance analysis

### Maintenance Tools
- `manage-dependencies.sh` - Dependency management
- `verify-mcp-setup.sh` - Service verification

## API Endpoints

- **MCP Server**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **Redis**: localhost:6379

## Configuration

### Environment Variables
```bash
# Required
XAI_API_KEY=your_xai_api_key

# Optional
ANTHROPIC_API_KEY=your_claude_key
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379
```

### Docker Compose
```yaml
version: '3.8'
services:
  grokputer:
    image: grokputer-mcp-alpine:latest
    ports:
      - "8000:8000"
      - "6379:6379"
    env_file:
      - .env
    volumes:
      - ./vault:/app/vault
      - ./logs:/app/logs
```

## Development

### Running Tests
```bash
./automate.sh test
```

### Code Quality
```bash
./automate.sh quality
```

### Performance Analysis
```bash
./optimize-performance.sh all
```

## Deployment

### Staging
```bash
./deploy.sh staging
```

### Production
```bash
./deploy.sh production
```

### Monitoring
```bash
./monitor.sh start
```

## Documentation

- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Performance Guide](docs/performance.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Automation Guide](AUTOMATION-README.md)

## Contributing

1. Fork the repository
2. Create a feature branch: `./git-workflow.sh feature`
3. Make changes and run tests: `./automate.sh quality test`
4. Submit a pull request

## Security

- Automated security scanning
- Dependency vulnerability checks
- Secrets detection
- Regular security updates

## License

See LICENSE file for details.

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issues](https://github.com/your-repo/issues)
- 💬 [Discussions](https://github.com/your-repo/discussions)

---

**Built with ❤️ using cutting-edge automation**
EOF

    echo -e "${GREEN}✓ README generated${NC}"
}

# Function to update all documentation
update_all_docs() {
    echo -e "${BLUE}Updating all documentation...${NC}"

    generate_api_docs
    generate_code_docs
    generate_deployment_docs
    generate_performance_docs
    generate_troubleshooting_docs
    generate_readme

    echo -e "${GREEN}✓ All documentation updated${NC}"
}

# Function to check documentation completeness
check_docs_completeness() {
    echo -e "${BLUE}Checking documentation completeness...${NC}"

    local missing_docs=()

    # Check for required documentation files
    local required_docs=("README.md" "docs/api.md" "docs/deployment.md" "docs/troubleshooting.md")

    for doc in "${required_docs[@]}"; do
        if [ ! -f "$doc" ]; then
            missing_docs+=("$doc")
        fi
    done

    if [ ${#missing_docs[@]} -gt 0 ]; then
        echo -e "${YELLOW}Missing documentation files:${NC}"
        printf '  • %s\n' "${missing_docs[@]}"
        return 1
    else
        echo -e "${GREEN}✓ All required documentation present${NC}"
    fi

    # Check for outdated documentation
    local readme_age
    readme_age=$(stat -c %Y README.md 2>/dev/null || stat -f %m README.md 2>/dev/null || echo "0")
    local current_time
    current_time=$(date +%s)
    local days_old=$(( (current_time - readme_age) / 86400 ))

    if [ "$days_old" -gt 30 ]; then
        echo -e "${YELLOW}⚠️  README is $days_old days old - consider updating${NC}"
    fi
}

# Main execution
case "${1:-all}" in
    "api")
        generate_api_docs ;;
    "code")
        generate_code_docs ;;
    "deployment")
        generate_deployment_docs ;;
    "performance")
        generate_performance_docs ;;
    "troubleshooting")
        generate_troubleshooting_docs ;;
    "readme")
        generate_readme ;;
    "check")
        check_docs_completeness ;;
    "all")
        update_all_docs
        check_docs_completeness ;;
    "help"|"-h"|"--help")
        echo "Documentation Automation Tool"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  api            - Generate API documentation"
        echo "  code           - Generate code documentation"
        echo "  deployment     - Generate deployment docs"
        echo "  performance    - Generate performance docs"
        echo "  troubleshooting- Generate troubleshooting docs"
        echo "  readme         - Generate README"
        echo "  check          - Check documentation completeness"
        echo "  all            - Update all documentation"
        echo "  help           - Show this help"
        ;;
    *)
        echo "Unknown command: $1"
        "$0" help
        exit 1
        ;;
esac

echo -e "${GREEN}Documentation automation completed!${NC}"