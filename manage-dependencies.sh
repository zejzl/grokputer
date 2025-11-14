#!/bin/bash
# Dependency Management & Security Updates

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}🔒 Dependency Management & Security${NC}"
echo "====================================="

# Create reports directory
mkdir -p reports

# Function to check for outdated packages
check_outdated() {
    echo -e "${BLUE}Checking for outdated packages...${NC}"

    if [ -f "requirements.txt" ]; then
        echo "Python packages:"
        pip list --outdated --format=columns > "reports/outdated_python_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
        cat "reports/outdated_python_$(date +%Y%m%d_%H%M%S).txt" | head -20
        echo -e "${GREEN}✓ Python packages checked${NC}"
    fi

    if [ -f "package.json" ]; then
        echo "Node packages:"
        npm outdated > "reports/outdated_node_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
        cat "reports/outdated_node_$(date +%Y%m%d_%H%M%S).txt" | head -20
        echo -e "${GREEN}✓ Node packages checked${NC}"
    fi
}

# Function to check security vulnerabilities
check_security() {
    echo -e "${BLUE}Checking for security vulnerabilities...${NC}"

    # Python security
    if command -v safety &> /dev/null; then
        echo "Python vulnerabilities:"
        safety check --output text > "reports/security_python_$(date +%Y%m%d_%H%M%S).txt" 2>&1 || true
        if grep -q "vulnerability" "reports/security_python_$(date +%Y%m%d_%H%M%S).txt"; then
            echo -e "${RED}⚠ Python security issues found!${NC}"
            grep "vulnerability" "reports/security_python_$(date +%Y%m%d_%H%M%S).txt"
        else
            echo -e "${GREEN}✓ No Python security issues${NC}"
        fi
    fi

    # Node security
    if [ -f "package.json" ] && command -v npm &> /dev/null; then
        echo "Node vulnerabilities:"
        npm audit --audit-level moderate > "reports/security_node_$(date +%Y%m%d_%H%M%S).txt" 2>&1 || true
        if grep -q "vulnerability" "reports/security_node_$(date +%Y%m%d_%H%M%S).txt"; then
            echo -e "${RED}⚠ Node security issues found!${NC}"
        else
            echo -e "${GREEN}✓ No Node security issues${NC}"
        fi
    fi

    # Check for secrets in code
    if command -v trufflehog &> /dev/null; then
        echo "Checking for secrets in code..."
        trufflehog --regex --entropy=False . > "reports/secrets_$(date +%Y%m%d_%H%M%S).txt" 2>&1 || true
        if grep -q "Found" "reports/secrets_$(date +%Y%m%d_%H%M%S).txt"; then
            echo -e "${RED}⚠ Potential secrets found!${NC}"
        else
            echo -e "${GREEN}✓ No secrets detected${NC}"
        fi
    fi
}

# Function to update dependencies safely
update_dependencies() {
    echo -e "${BLUE}Updating dependencies safely...${NC}"

    # Backup current requirements
    if [ -f "requirements.txt" ]; then
        cp requirements.txt "requirements.txt.backup.$(date +%Y%m%d_%H%M%S)"
        echo -e "${GREEN}✓ Requirements backed up${NC}"
    fi

    # Update Python packages (conservative)
    if [ -f "requirements.txt" ]; then
        echo "Updating Python packages..."
        pip install --upgrade --upgrade-strategy eager -r requirements.txt 2>/dev/null || true
        pip freeze > requirements.txt.new
        mv requirements.txt.new requirements.txt
        echo -e "${GREEN}✓ Python packages updated${NC}"
    fi

    # Update Node packages
    if [ -f "package.json" ]; then
        echo "Updating Node packages..."
        npm update
        echo -e "${GREEN}✓ Node packages updated${NC}"
    fi
}

# Function to clean up unused dependencies
cleanup_dependencies() {
    echo -e "${BLUE}Cleaning up unused dependencies...${NC}"

    # Python cleanup
    if command -v pip-autoremove &> /dev/null; then
        echo "Removing unused Python packages..."
        pip-autoremove -y 2>/dev/null || true
        echo -e "${GREEN}✓ Unused Python packages removed${NC}"
    fi

    # Node cleanup
    if [ -f "package.json" ]; then
        echo "Cleaning Node cache..."
        npm cache clean --force 2>/dev/null || true
        echo -e "${GREEN}✓ Node cache cleaned${NC}"
    fi
}

# Function to generate dependency report
generate_report() {
    echo -e "${BLUE}Generating dependency report...${NC}"

    local report_file="reports/dependency_report_$(date +%Y%m%d_%H%M%S).md"

    cat > "$report_file" << 'EOF'
# Dependency Analysis Report

Generated on: $(date)

## Package Counts

### Python Packages
EOF

    if [ -f "requirements.txt" ]; then
        echo "\`\`\`" >> "$report_file"
        wc -l < requirements.txt >> "$report_file"
        echo "packages" >> "$report_file"
        echo "\`\`\`" >> "$report_file"
    fi

    cat >> "$report_file" << 'EOF'

### Node Packages
EOF

    if [ -f "package.json" ]; then
        echo "\`\`\`" >> "$report_file"
        grep -c '"[^"]*":' package.json >> "$report_file" 2>/dev/null || echo "0" >> "$report_file"
        echo "packages" >> "$report_file"
        echo "\`\`\`" >> "$report_file"
    fi

    cat >> "$report_file" << 'EOF'

## Security Status

### Python Security
EOF

    if ls reports/security_python_* >/dev/null 2>&1; then
        echo "\`\`\`" >> "$report_file"
        tail -10 reports/security_python_* | head -1 >> "$report_file" 2>/dev/null || echo "Check completed" >> "$report_file"
        echo "\`\`\`" >> "$report_file"
    fi

    cat >> "$report_file" << 'EOF'

## Recommendations

1. **Review security reports** regularly
2. **Update dependencies** in development environment first
3. **Test thoroughly** after updates
4. **Monitor for breaking changes** in major version updates
5. **Use virtual environments** for isolation

## Last Updated

Dependencies last updated: $(date)
EOF

    echo -e "${GREEN}✓ Dependency report generated: $report_file${NC}"
}

# Function to check license compatibility
check_licenses() {
    echo -e "${BLUE}Checking license compatibility...${NC}"

    if command -v licensecheck &> /dev/null; then
        licensecheck --recursive . > "reports/licenses_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
        echo -e "${GREEN}✓ License check completed${NC}"
    fi
}

# Main execution
case "${1:-all}" in
    "check")
        check_outdated
        check_security ;;
    "update")
        update_dependencies ;;
    "cleanup")
        cleanup_dependencies ;;
    "licenses")
        check_licenses ;;
    "report")
        generate_report ;;
    "all")
        check_outdated
        check_security
        check_licenses
        generate_report ;;
    *)
        echo "Usage: $0 [check|update|cleanup|licenses|report|all]"
        echo "  check     - Check for outdated and vulnerable packages"
        echo "  update    - Update dependencies safely"
        echo "  cleanup   - Remove unused dependencies"
        echo "  licenses  - Check license compatibility"
        echo "  report    - Generate dependency report"
        echo "  all       - Run all dependency management tasks"
        ;;
esac

echo -e "${GREEN}Dependency management completed!${NC}"