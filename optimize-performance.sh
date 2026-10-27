#!/bin/bash
# Performance Monitoring & Optimization Script

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Performance Monitoring & Optimization${NC}"
echo "=========================================="

# Create reports directory
mkdir -p reports

# Function to run performance tests
run_performance_tests() {
    echo -e "${BLUE}Running Performance Tests...${NC}"

    # Memory usage test
    if command -v memory_profiler &> /dev/null; then
        echo "Memory profiling main.py..."
        python -m memory_profiler main.py --help 2>/dev/null > "reports/memory_profile_$(date +%Y%m%d_%H%M%S).txt" || true
        echo -e "${GREEN}✓ Memory profile generated${NC}"
    fi

    # CPU profiling
    if command -v cProfile &> /dev/null; then
        echo "CPU profiling main.py..."
        python -c "import cProfile; import main; cProfile.run('main.main()', 'reports/cpu_profile.prof')" 2>/dev/null || true
        echo -e "${GREEN}✓ CPU profile generated${NC}"
    fi

    # Line profiling for slow functions
    if command -v line_profiler &> /dev/null; then
        echo "Line profiling key functions..."
        kernprof -l -o reports/line_profile.lprof main.py --help 2>/dev/null || true
        echo -e "${GREEN}✓ Line profile generated${NC}"
    fi
}

# Function to analyze code complexity
analyze_complexity() {
    echo -e "${BLUE}Analyzing Code Complexity...${NC}"

    if command -v radon &> /dev/null; then
        echo "Calculating cyclomatic complexity..."
        radon cc src/ -a -s > "reports/complexity_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
        echo -e "${GREEN}✓ Complexity analysis completed${NC}"

        echo "Calculating maintainability index..."
        radon mi src/ > "reports/maintainability_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
        echo -e "${GREEN}✓ Maintainability analysis completed${NC}"
    fi
}

# Function to check for performance bottlenecks
check_bottlenecks() {
    echo -e "${BLUE}Checking for Performance Bottlenecks...${NC}"

    # Find large files
    echo "Finding largest Python files..."
    find src/ -name "*.py" -exec wc -l {} \; | sort -nr | head -10 > "reports/large_files_$(date +%Y%m%d_%H%M%S).txt"
    echo -e "${GREEN}✓ Large files report generated${NC}"

    # Check for inefficient patterns
    echo "Checking for inefficient patterns..."
    grep -r "import \*" src/ --include="*.py" > "reports/star_imports_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
    grep -r "print(" src/ --include="*.py" | wc -l > "reports/print_statements_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
    echo -e "${GREEN}✓ Inefficient patterns checked${NC}"
}

# Function to optimize imports
optimize_imports() {
    echo -e "${BLUE}Optimizing Imports...${NC}"

    if command -v isort &> /dev/null; then
        echo "Sorting imports..."
        isort src/ --profile black
        echo -e "${GREEN}✓ Imports sorted${NC}"
    fi

    if command -v autoflake &> /dev/null; then
        echo "Removing unused imports..."
        autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place src/
        echo -e "${GREEN}✓ Unused imports removed${NC}"
    fi
}

# Function to generate performance report
generate_report() {
    echo -e "${BLUE}Generating Performance Report...${NC}"

    local report_file="reports/performance_report_$(date +%Y%m%d_%H%M%S).md"

    cat > "$report_file" << 'EOF'
# Performance Analysis Report

Generated on: $(date)

## System Information
- OS: $(uname -a)
- Python: $(python --version 2>&1)
- Memory: $(free -h | grep Mem | awk '{print $2}' 2>/dev/null || echo "N/A")

## Key Metrics

### Code Complexity
EOF

    if [ -f "reports/complexity_$(date +%Y%m%d)*.txt" ]; then
        echo "\`\`\`" >> "$report_file"
        tail -20 "reports/complexity_$(date +%Y%m%d)*.txt" >> "$report_file" 2>/dev/null || true
        echo "\`\`\`" >> "$report_file"
    fi

    cat >> "$report_file" << 'EOF'

### Largest Files
EOF

    if [ -f "reports/large_files_$(date +%Y%m%d)*.txt" ]; then
        echo "\`\`\`" >> "$report_file"
        cat "reports/large_files_$(date +%Y%m%d)*.txt" >> "$report_file" 2>/dev/null || true
        echo "\`\`\`" >> "$report_file"
    fi

    cat >> "$report_file" << 'EOF'

## Recommendations

1. **Review complex functions** with high cyclomatic complexity
2. **Consider breaking down** large files (>500 lines)
3. **Remove debug prints** from production code
4. **Use specific imports** instead of `import *`
5. **Profile memory usage** for memory-intensive operations

## Next Steps

- Run performance tests regularly
- Monitor memory usage in production
- Review and refactor complex functions
- Consider async/await for I/O operations
EOF

    echo -e "${GREEN}✓ Performance report generated: $report_file${NC}"
}

# Main execution
case "${1:-all}" in
    "test")
        run_performance_tests ;;
    "complexity")
        analyze_complexity ;;
    "bottlenecks")
        check_bottlenecks ;;
    "optimize")
        optimize_imports ;;
    "report")
        generate_report ;;
    "all")
        run_performance_tests
        analyze_complexity
        check_bottlenecks
        optimize_imports
        generate_report ;;
    *)
        echo "Usage: $0 [test|complexity|bottlenecks|optimize|report|all]"
        echo "  test       - Run performance tests"
        echo "  complexity - Analyze code complexity"
        echo "  bottlenecks- Check for performance bottlenecks"
        echo "  optimize   - Optimize imports and code"
        echo "  report     - Generate performance report"
        echo "  all        - Run all performance checks"
        ;;
esac

echo -e "${GREEN}Performance analysis completed!${NC}"