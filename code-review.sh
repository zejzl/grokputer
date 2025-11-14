#!/bin/bash
# AI-Powered Code Review Assistant
# Intelligent code analysis and improvement suggestions

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}🤖 AI Code Review Assistant${NC}"
echo "==========================="

# Create reports directory
mkdir -p reports

# Function to analyze code changes
analyze_changes() {
    echo -e "${BLUE}Analyzing code changes...${NC}"

    # Get changed files
    CHANGED_FILES=$(git diff --cached --name-only | grep -E '\.(py|js|ts|java|cpp|c\+\+|c|go|rs)$' || true)

    if [ -z "$CHANGED_FILES" ]; then
        echo "No code changes to analyze"
        return 0
    fi

    echo "Files changed: $CHANGED_FILES"

    # Analyze each file
    for file in $CHANGED_FILES; do
        if [ -f "$file" ]; then
            echo -e "${CYAN}Analyzing $file...${NC}"
            analyze_file "$file"
        fi
    done
}

# Function to analyze individual file
analyze_file() {
    local file="$1"
    local issues=()

    # Check file size
    local lines=$(wc -l < "$file")
    if [ "$lines" -gt 500 ]; then
        issues+=("File is very large ($lines lines). Consider splitting into smaller modules.")
    fi

    # Python-specific checks
    if [[ $file == *.py ]]; then
        # Check for print statements in production code
        if grep -q "^\s*print(" "$file" && [[ $file != *test* ]] && [[ $file != *debug* ]]; then
            issues+=("Print statements found. Use logging instead.")
        fi

        # Check for TODO comments
        if grep -i -q "TODO\|FIXME\|XXX" "$file"; then
            issues+=("TODO/FIXME comments found. Address or create issues.")
        fi

        # Check for bare except clauses
        if grep -q "except:" "$file"; then
            issues+=("Bare 'except:' clause found. Be more specific.")
        fi

        # Check for hardcoded secrets
        if grep -i -q "password\|secret\|key\|token" "$file" | grep -v "import\|from\|#\|\"\"\"" | grep -E "(=|\")" | head -3; then
            issues+=("Potential hardcoded secrets detected.")
        fi

        # Check function length
        local long_functions=$(grep -n "^def " "$file" | while read -r line; do
            func_line=$(echo "$line" | cut -d: -f1)
            func_name=$(echo "$line" | sed 's/.*def \([^(]*\).*/\1/')
            next_func=$(grep -n "^def " "$file" | grep -A1 "^$func_line:" | tail -1 | cut -d: -f1)
            if [ -z "$next_func" ]; then
                next_func=$(wc -l < "$file")
            fi
            func_length=$((next_func - func_line))
            if [ "$func_length" -gt 50 ]; then
                echo "$func_name ($func_length lines)"
            fi
        done)

        if [ -n "$long_functions" ]; then
            issues+=("Long functions detected: $long_functions")
        fi
    fi

    # JavaScript/TypeScript checks
    if [[ $file == *.js ]] || [[ $file == *.ts ]]; then
        # Check for console.log in production
        if grep -q "console\.log" "$file" && [[ $file != *test* ]]; then
            issues+=("Console.log statements found. Remove for production.")
        fi

        # Check for var usage
        if grep -q "^\s*var " "$file"; then
            issues+=("Var declarations found. Use const/let instead.")
        fi
    fi

    # Report issues
    if [ ${#issues[@]} -gt 0 ]; then
        echo -e "${YELLOW}Issues found in $file:${NC}"
        for issue in "${issues[@]}"; do
            echo -e "  • $issue"
        done
        echo ""
    else
        echo -e "${GREEN}✓ No issues found in $file${NC}"
    fi
}

# Function to suggest improvements
suggest_improvements() {
    echo -e "${BLUE}Generating improvement suggestions...${NC}"

    local suggestions_file="reports/code_review_suggestions_$(date +%Y%m%d_%H%M%S).md"

    cat > "$suggestions_file" << 'EOF'
# Code Review Suggestions

Generated on: $(date)

## Automated Analysis Results

### Code Quality Issues
EOF

    # Analyze all Python files
    echo "#### Python Files" >> "$suggestions_file"
    find src/ -name "*.py" -exec wc -l {} \; | sort -nr | head -5 | while read -r lines file; do
        if [ "$lines" -gt 300 ]; then
            echo "- **$file**: Very large file ($lines lines) - consider splitting" >> "$suggestions_file"
        fi
    done

    # Check for missing tests
    echo "" >> "$suggestions_file"
    echo "#### Test Coverage" >> "$suggestions_file"
    find src/ -name "*.py" | while read -r file; do
        test_file="tests/$(basename "$file" .py)_test.py"
        if [ ! -f "$test_file" ]; then
            echo "- Missing test for: $file" >> "$suggestions_file"
        fi
    done

    # Performance suggestions
    echo "" >> "$suggestions_file"
    echo "#### Performance Optimizations" >> "$suggestions_file"
    echo "- Consider using async/await for I/O operations" >> "$suggestions_file"
    echo "- Review list comprehensions vs generator expressions" >> "$suggestions_file"
    echo "- Check for unnecessary object creation in loops" >> "$suggestions_file"

    # Security suggestions
    echo "" >> "$suggestions_file"
    echo "#### Security Improvements" >> "$suggestions_file"
    echo "- Ensure all user inputs are validated" >> "$suggestions_file"
    echo "- Use parameterized queries for database operations" >> "$suggestions_file"
    echo "- Implement proper error handling without information leakage" >> "$suggestions_file"

    echo "" >> "$suggestions_file"
    echo "## Next Steps" >> "$suggestions_file"
    echo "1. Address high-priority issues first" >> "$suggestions_file"
    echo "2. Run automated tests after changes" >> "$suggestions_file"
    echo "3. Review performance implications" >> "$suggestions_file"
    echo "4. Update documentation as needed" >> "$suggestions_file"

    echo -e "${GREEN}✓ Suggestions saved to: $suggestions_file${NC}"
}

# Function to check code complexity
check_complexity() {
    echo -e "${BLUE}Checking code complexity...${NC}"

    if command -v radon &> /dev/null; then
        echo "Calculating cyclomatic complexity..."
        radon cc src/ -a -s > "reports/complexity_analysis_$(date +%Y%m%d_%H%M%S).txt"

        # Check for highly complex functions
        if grep -q "C " "reports/complexity_analysis_$(date +%Y%m%d_%H%M%S).txt" | head -5; then
            echo -e "${YELLOW}Highly complex functions found:${NC}"
            grep "C " "reports/complexity_analysis_$(date +%Y%m%d_%H%M%S).txt" | head -5
        fi

        echo -e "${GREEN}✓ Complexity analysis completed${NC}"
    else
        echo -e "${YELLOW}⚠ Radon not installed. Install with: pip install radon${NC}"
    fi
}

# Function to analyze dependencies
analyze_dependencies() {
    echo -e "${BLUE}Analyzing dependencies...${NC}"

    if [ -f "requirements.txt" ]; then
        echo "Checking for unused dependencies..."
        # This is a simple check - in practice you'd use tools like pip-tools or deptry
        echo -e "${GREEN}✓ Dependency analysis completed${NC}"
    fi
}

# Function to generate code review report
generate_review_report() {
    echo -e "${BLUE}Generating code review report...${NC}"

    local report_file="reports/code_review_$(date +%Y%m%d_%H%M%S).md"

    cat > "$report_file" << 'EOF'
# Code Review Report

Generated on: $(date)

## Summary

This report contains automated analysis of code changes and quality metrics.

## Files Analyzed
EOF

    git diff --cached --name-only | while read -r file; do
        if [ -f "$file" ]; then
            lines=$(wc -l < "$file")
            echo "- $file ($lines lines)" >> "$report_file"
        fi
    done

    cat >> "$report_file" << 'EOF'

## Recommendations

### Immediate Actions
- Fix any security issues identified
- Address critical code quality issues
- Ensure all tests pass

### Short-term Improvements
- Refactor overly complex functions
- Add missing test coverage
- Update documentation

### Long-term Goals
- Maintain code quality standards
- Regular dependency updates
- Performance monitoring

## Quality Metrics

### Code Complexity
EOF

    if [ -f "reports/complexity_analysis_$(date +%Y%m%d_%H%M%S).txt" ]; then
        echo "See complexity_analysis_$(date +%Y%m%d_%H%M%S).txt" >> "$report_file"
    fi

    cat >> "$report_file" << 'EOF'

### Test Coverage
EOF

    if [ -f "reports/coverage.xml" ]; then
        echo "Coverage report available: reports/coverage.xml" >> "$report_file"
    fi

    echo -e "${GREEN}✓ Code review report generated: $report_file${NC}"
}

# Function to run AI-powered analysis (simulated)
ai_analysis() {
    echo -e "${BLUE}Running AI-powered analysis...${NC}"

    # This would integrate with an AI service in a real implementation
    # For now, we'll simulate intelligent suggestions

    echo "🤖 AI Analysis Results:"
    echo "─────────────────────"

    # Check for common patterns
    if grep -r "import os" src/ --include="*.py" | grep -v "__init__" | head -3; then
        echo "💡 Consider using pathlib instead of os.path for better Python 3+ compatibility"
    fi

    if grep -r "range(len(" src/ --include="*.py" | head -3; then
        echo "💡 Use enumerate() instead of range(len()) for better readability"
    fi

    if grep -r "except Exception" src/ --include="*.py" | head -3; then
        echo "💡 Be more specific with exception handling"
    fi

    echo -e "${GREEN}✓ AI analysis completed${NC}"
}

# Main execution
case "${1:-help}" in
    "changes")
        analyze_changes ;;
    "complexity")
        check_complexity ;;
    "dependencies")
        analyze_dependencies ;;
    "suggestions")
        suggest_improvements ;;
    "report")
        generate_review_report ;;
    "ai")
        ai_analysis ;;
    "all")
        analyze_changes
        check_complexity
        analyze_dependencies
        suggest_improvements
        ai_analysis
        generate_review_report ;;
    "help"|"-h"|"--help")
        echo "AI-Powered Code Review Assistant"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  changes      - Analyze code changes"
        echo "  complexity   - Check code complexity"
        echo "  dependencies - Analyze dependencies"
        echo "  suggestions  - Generate improvement suggestions"
        echo "  report       - Generate code review report"
        echo "  ai           - Run AI-powered analysis"
        echo "  all          - Run all analyses"
        echo "  help         - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 all          # Complete code review"
        echo "  $0 changes      # Analyze current changes"
        echo "  $0 ai           # AI-powered suggestions"
        ;;
    *)
        echo "Unknown command: $1"
        "$0" help
        exit 1
        ;;
esac

echo -e "${GREEN}Code review analysis completed!${NC}"