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

# One timestamp per run, so every report file is written and read under the same name
TS=$(date +%Y%m%d_%H%M%S)

# Set to 1 when a check finds real problems (vulnerabilities); makes the script exit nonzero
ISSUES_FOUND=0

# Function to check for outdated packages
check_outdated() {
    echo -e "${BLUE}Checking for outdated packages...${NC}"

    if [ -f "requirements.txt" ]; then
        echo "Python packages:"
        local out="reports/outdated_python_${TS}.txt"
        pip list --outdated --format=columns > "$out" 2>/dev/null || true
        head -20 "$out"
        echo -e "${GREEN}✓ Python packages checked${NC}"
    fi

    if [ -f "package.json" ]; then
        echo "Node packages:"
        local out="reports/outdated_node_${TS}.txt"
        # npm outdated exits 1 when anything is outdated, which is not an error here
        npm outdated > "$out" 2>/dev/null || true
        head -20 "$out"
        echo -e "${GREEN}✓ Node packages checked${NC}"
    fi
}

# Function to check security vulnerabilities
check_security() {
    echo -e "${BLUE}Checking for security vulnerabilities...${NC}"

    # Python security
    if command -v safety &> /dev/null; then
        echo "Python vulnerabilities:"
        local out="reports/security_python_${TS}.txt"
        safety check --output text > "$out" 2>&1 || true
        if grep -q "vulnerabilit" "$out"; then
            echo -e "${RED}⚠ Python security issues found!${NC}"
            grep "vulnerabilit" "$out"
            ISSUES_FOUND=1
        else
            echo -e "${GREEN}✓ No Python security issues${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Python vulnerability check skipped (safety not installed)${NC}"
    fi

    # Node security
    if [ -f "package.json" ] && command -v npm &> /dev/null; then
        echo "Node vulnerabilities:"
        local out="reports/security_node_${TS}.txt"
        npm audit --audit-level moderate > "$out" 2>&1 || true
        if grep -qE "npm ERR|ENOLOCK|audit endpoint" "$out"; then
            echo -e "${YELLOW}⚠ Node audit could not run (see $out)${NC}"
        elif grep -qE "[1-9][0-9]* (low|moderate|high|critical)|found [1-9]" "$out"; then
            echo -e "${RED}⚠ Node security issues found! (see $out)${NC}"
            ISSUES_FOUND=1
        else
            echo -e "${GREEN}✓ No Node security issues${NC}"
        fi
    fi

    # Check for secrets in code
    if command -v trufflehog &> /dev/null; then
        echo "Checking for secrets in code..."
        local out="reports/secrets_${TS}.txt"
        trufflehog --regex --entropy=False . > "$out" 2>&1 || true
        if grep -q "Found" "$out"; then
            echo -e "${RED}⚠ Potential secrets found!${NC}"
            ISSUES_FOUND=1
        else
            echo -e "${GREEN}✓ No secrets detected${NC}"
        fi
    fi
}

# Function to update dependencies. Dry run unless DEPS_APPLY=1: requirements.txt pins
# versions on purpose (e.g. huggingface-hub), so it is never rewritten from pip freeze.
update_dependencies() {
    if [ "${DEPS_APPLY:-0}" != "1" ]; then
        echo -e "${YELLOW}Dry run: nothing is upgraded. Set DEPS_APPLY=1 to apply.${NC}"
        check_outdated
        return 0
    fi

    echo -e "${BLUE}Updating dependencies...${NC}"

    if [ -f "requirements.txt" ]; then
        cp requirements.txt "requirements.txt.backup.${TS}"
        echo -e "${GREEN}✓ Requirements backed up${NC}"
        echo "Upgrading Python packages within the pins in requirements.txt..."
        pip install -r requirements.txt
        echo -e "${GREEN}✓ Python packages installed${NC}"
    fi

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

    local report_file="reports/dependency_report_${TS}.md"

    cat > "$report_file" << EOF
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

    cat >> "$report_file" << EOF

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
        licensecheck --recursive . > "reports/licenses_${TS}.txt" 2>/dev/null || true
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

exit "$ISSUES_FOUND"
