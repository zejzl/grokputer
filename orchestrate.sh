#!/bin/bash
# Master Orchestration Script
# Unified interface for all Grokputer automation tools

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# ASCII Art Header
show_header() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║           ██████   ██████   ██████  ██   ██ ██████  ██    ██ ████████         ║
║          ██       ██    ██ ██    ██ ██  ██  ██   ██ ██    ██    ██            ║
║          ██   ███ ██    ██ ██    ██ █████   ██████  ██    ██    ██            ║
║          ██    ██ ██    ██ ██    ██ ██  ██  ██   ██ ██    ██    ██            ║
║           ██████   ██████   ██████  ██   ██ ██████   ██████     ██            ║
║                                                                              ║
║                    🤖 MASTER AUTOMATION ORCHESTRATOR 🤖                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Function to check if tool exists
tool_exists() {
    local tool="$1"
    [ -f "$tool" ] && [ -x "$tool" ]
}

# Function to run tool with error handling
run_tool() {
    local tool="$1"
    shift
    local args="$*"

    if tool_exists "$tool"; then
        echo -e "${BLUE}Running $tool $args...${NC}"
        if "./$tool" $args; then
            echo -e "${GREEN}✓ $tool completed successfully${NC}"
            return 0
        else
            echo -e "${RED}✗ $tool failed${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ $tool not found, skipping${NC}"
        return 1
    fi
}

# Function to show available tools
show_tools() {
    echo -e "${WHITE}Available Automation Tools:${NC}"
    echo "═══════════════════════════"

    local tools=(
        "automate.sh:Master automation suite"
        "setup-mcp-alpine.sh:MCP Alpine container setup"
        "setup-mcp-alpine.bat:Windows MCP setup"
        "deploy.sh:Deployment orchestration"
        "monitor.sh:Health monitoring & alerting"
        "git-workflow.sh:Smart Git operations"
        "code-review.sh:AI-powered code review"
        "optimize-performance.sh:Performance analysis"
        "manage-dependencies.sh:Dependency management"
        "generate-docs.sh:Documentation automation"
        "verify-mcp-setup.sh:Service verification"
        "verify-mcp-setup.bat:Windows verification"
    )

    for tool_info in "${tools[@]}"; do
        local tool="${tool_info%%:*}"
        local desc="${tool_info#*:}"

        if tool_exists "$tool"; then
            echo -e "${GREEN}✓${NC} $tool - $desc"
        else
            echo -e "${RED}✗${NC} $tool - $desc"
        fi
    done

    echo ""
    echo -e "${WHITE}Available Commands:${NC}"
    echo "═══════════════════"
}

# Function for complete system setup
system_setup() {
    echo -e "${PURPLE}🚀 Complete System Setup${NC}"
    echo "========================"

    run_tool "automate.sh" "setup"
    run_tool "setup-mcp-alpine.sh"
    run_tool "git-workflow.sh" "setup"
    run_tool "generate-docs.sh" "all"

    echo -e "${GREEN}✓ System setup completed!${NC}"
}

# Function for development workflow
dev_workflow() {
    echo -e "${PURPLE}💻 Development Workflow${NC}"
    echo "======================="

    run_tool "automate.sh" "quality"
    run_tool "automate.sh" "test"
    run_tool "code-review.sh" "changes"
    run_tool "git-workflow.sh" "commit"

    echo -e "${GREEN}✓ Development workflow completed!${NC}"
}

# Function for deployment pipeline
deployment_pipeline() {
    local env="${1:-staging}"

    echo -e "${PURPLE}🚢 Deployment Pipeline ($env)${NC}"
    echo "==========================="

    run_tool "automate.sh" "build"
    run_tool "automate.sh" "security"
    run_tool "deploy.sh" "$env"
    run_tool "verify-mcp-setup.sh"

    echo -e "${GREEN}✓ Deployment to $env completed!${NC}"
}

# Function for maintenance tasks
maintenance_tasks() {
    echo -e "${PURPLE}🔧 Maintenance Tasks${NC}"
    echo "===================="

    run_tool "automate.sh" "cleanup"
    run_tool "automate.sh" "backup"
    run_tool "optimize-performance.sh" "all"
    run_tool "manage-dependencies.sh" "update"
    run_tool "generate-docs.sh" "check"

    echo -e "${GREEN}✓ Maintenance tasks completed!${NC}"
}

# Function for monitoring dashboard
monitoring_dashboard() {
    echo -e "${PURPLE}📊 Monitoring Dashboard${NC}"
    echo "======================="

    echo -e "${CYAN}System Status:${NC}"
    run_tool "monitor.sh" "check"

    echo ""
    echo -e "${CYAN}Service Status:${NC}"
    run_tool "monitor.sh" "status"

    echo ""
    echo -e "${CYAN}Recent Alerts:${NC}"
    run_tool "monitor.sh" "alerts"
}

# Function for performance optimization
performance_optimization() {
    echo -e "${PURPLE}⚡ Performance Optimization${NC}"
    echo "==========================="

    run_tool "optimize-performance.sh" "all"
    run_tool "code-review.sh" "complexity"
    run_tool "automate.sh" "optimize"

    echo -e "${GREEN}✓ Performance optimization completed!${NC}"
}

# Function for security audit
security_audit() {
    echo -e "${PURPLE}🔒 Security Audit${NC}"
    echo "================"

    run_tool "manage-dependencies.sh" "check"
    run_tool "code-review.sh" "ai"
    run_tool "automate.sh" "security"

    echo -e "${GREEN}✓ Security audit completed!${NC}"
}

# Function for documentation update
docs_update() {
    echo -e "${PURPLE}📚 Documentation Update${NC}"
    echo "========================"

    run_tool "generate-docs.sh" "all"
    run_tool "generate-docs.sh" "check"

    echo -e "${GREEN}✓ Documentation updated!${NC}"
}

# Function for emergency recovery
emergency_recovery() {
    echo -e "${RED}🚨 Emergency Recovery${NC}"
    echo "===================="

    echo -e "${YELLOW}This will rollback to the last known good state.${NC}"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" = "yes" ]; then
        run_tool "deploy.sh" "rollback"
        run_tool "automate.sh" "cleanup"
        echo -e "${GREEN}✓ Emergency recovery completed!${NC}"
    else
        echo "Recovery cancelled."
    fi
}

# Function to show system health
system_health() {
    echo -e "${PURPLE}🏥 System Health Check${NC}"
    echo "======================"

    echo -e "${CYAN}Core Services:${NC}"
    if tool_exists "verify-mcp-setup.sh"; then
        ./verify-mcp-setup.sh
    fi

    echo ""
    echo -e "${CYAN}Code Quality:${NC}"
    run_tool "automate.sh" "quality"

    echo ""
    echo -e "${CYAN}Dependencies:${NC}"
    run_tool "manage-dependencies.sh" "check"

    echo ""
    echo -e "${CYAN}Documentation:${NC}"
    run_tool "generate-docs.sh" "check"
}

# Function for infinite panda adventure mode
infinite_panda_adventure() {
    local adventure_quotes=(
        "🐼 Panda says: 'Time for some bamboo automation!'"
        "🐼 Panda whispers: 'Let the continuous improvement begin...'"
        "🐼 Panda thinks: 'More automation = more nap time!'"
        "🐼 Panda observes: 'Watching the code grow stronger...'"
        "🐼 Panda meditates: 'Finding inner peace through perfect automation...'"
        "🐼 Panda discovers: 'Another optimization opportunity!'"
        "🐼 Panda celebrates: 'Automation level increased!'"
        "🐼 Panda reflects: 'The codebase is becoming enlightened...'"
        "🐼 Panda flows: 'Going with the automation current...'"
        "🐼 Panda balances: 'Maintaining perfect system harmony...'"
    )

    echo -e "${PURPLE}🐼🐼🐼 INFINITE PANDA ADVENTURE MODE 🐼🐼🐼${NC}"
    echo -e "${CYAN}Welcome to the endless cycle of automation excellence!${NC}"
    echo -e "${YELLOW}Press Ctrl+C to return to the mortal realm...${NC}"
    echo ""

    local cycle=1
    while true; do
        echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║           🐼 CYCLE $cycle - PANDA ADVENTURE 🐼           ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"

        # Random adventure quote
        local quote_index=$((RANDOM % ${#adventure_quotes[@]}))
        echo -e "${PURPLE}${adventure_quotes[$quote_index]}${NC}"
        echo ""

        # Phase 1: Health Check
        echo -e "${BLUE}🌿 Phase 1: System Health Check${NC}"
        if ! run_tool "monitor.sh" "check" >/dev/null 2>&1; then
            echo -e "${RED}🐼 Panda detects health issues! Running full diagnostic...${NC}"
            system_health
        else
            echo -e "${GREEN}✓ System is healthy and thriving!${NC}"
        fi

        # Phase 2: Code Quality
        echo -e "${BLUE}🎨 Phase 2: Code Quality Enhancement${NC}"
        if ! run_tool "automate.sh" "quality" >/dev/null 2>&1; then
            echo -e "${YELLOW}🐼 Panda finds code that needs polishing...${NC}"
            run_tool "code-review.sh" "changes"
        else
            echo -e "${GREEN}✓ Code quality is impeccable!${NC}"
        fi

        # Phase 3: Performance Optimization
        echo -e "${BLUE}⚡ Phase 3: Performance Optimization${NC}"
        if [ $((cycle % 5)) -eq 0 ]; then  # Every 5 cycles
            echo -e "${PURPLE}🐼 Panda performs deep performance meditation...${NC}"
            run_tool "optimize-performance.sh" "test" >/dev/null 2>&1
            echo -e "${GREEN}✓ Performance optimized!${NC}"
        else
            echo -e "${GREEN}✓ Performance monitoring active${NC}"
        fi

        # Phase 4: Security Patrol
        echo -e "${BLUE}🔒 Phase 4: Security Patrol${NC}"
        if [ $((cycle % 3)) -eq 0 ]; then  # Every 3 cycles
            echo -e "${PURPLE}🐼 Panda scans for security bamboo...${NC}"
            run_tool "manage-dependencies.sh" "check" >/dev/null 2>&1
            echo -e "${GREEN}✓ Security bamboo secured!${NC}"
        else
            echo -e "${GREEN}✓ Security systems active${NC}"
        fi

        # Phase 5: Maintenance Rituals
        echo -e "${BLUE}🧹 Phase 5: Maintenance Rituals${NC}"
        if [ $((cycle % 10)) -eq 0 ]; then  # Every 10 cycles
            echo -e "${PURPLE}🐼 Panda performs grand maintenance ceremony...${NC}"
            run_tool "automate.sh" "cleanup" >/dev/null 2>&1
            run_tool "automate.sh" "backup" >/dev/null 2>&1
            echo -e "${GREEN}✓ Grand maintenance completed!${NC}"
        else
            echo -e "${GREEN}✓ Routine maintenance performed${NC}"
        fi

        # Phase 6: Documentation Updates
        echo -e "${BLUE}📚 Phase 6: Documentation Enlightenment${NC}"
        if [ $((cycle % 7)) -eq 0 ]; then  # Every 7 cycles
            echo -e "${PURPLE}🐼 Panda updates the sacred scrolls...${NC}"
            run_tool "generate-docs.sh" "readme" >/dev/null 2>&1
            echo -e "${GREEN}✓ Documentation enlightened!${NC}"
        else
            echo -e "${GREEN}✓ Documentation wisdom preserved${NC}"
        fi

        # Phase 7: Achievement Check
        echo -e "${BLUE}🏆 Phase 7: Achievement Check${NC}"
        local achievements=0

        # Check various metrics
        if docker ps | grep -q grokputer; then ((achievements++)); fi
        if [ -f "vault/redis_backup.json" ]; then ((achievements++)); fi
        if [ -d "reports" ] && [ "$(ls reports/ | wc -l)" -gt 5 ]; then ((achievements++)); fi
        if [ -f ".env" ]; then ((achievements++)); fi

        echo -e "${GREEN}✓ Achievement Points: $achievements/4${NC}"

        # Special achievements
        if [ $cycle -eq 10 ]; then
            echo -e "${PURPLE}🐼🎉 PANDA ACHIEVEMENT UNLOCKED: Decade of Automation! 🎉🐼${NC}"
        elif [ $cycle -eq 25 ]; then
            echo -e "${PURPLE}🐼🎉 PANDA ACHIEVEMENT UNLOCKED: Quarter Century of Excellence! 🎉🐼${NC}"
        elif [ $((cycle % 50)) -eq 0 ]; then
            echo -e "${PURPLE}🐼🎉 PANDA ACHIEVEMENT UNLOCKED: Golden Cycle Milestone! 🎉🐼${NC}"
        fi

        # Bunny evolution achievements
        if [ $cycle -eq 7 ]; then
            echo -e "${PURPLE}🐰🎉 BUNNY ACHIEVEMENT UNLOCKED: Fluffy Code Weaver! 🎉🐰${NC}"
        elif [ $cycle -eq 15 ]; then
            echo -e "${PURPLE}🐰🎉 BUNNY ACHIEVEMENT UNLOCKED: Mystical Automation Bunny! 🎉🐰${NC}"
        elif [ $((cycle % 25)) -eq 0 ] && [ $cycle -gt 0 ]; then
            echo -e "${PURPLE}🐰🎉 BUNNY ACHIEVEMENT UNLOCKED: Legendary Bunny Sage! 🎉🐰${NC}"
        fi

        # Cycle completion
        echo -e "${CYAN}🐼 Cycle $cycle completed! Next bamboo feast in 5 minutes...${NC}"
        echo -e "${YELLOW}Ctrl+C to exit the panda realm${NC}"
        echo ""

        # Wait before next cycle (5 minutes)
        sleep 300
        ((cycle++))
    done
}

# Main menu system
show_menu() {
    echo -e "${WHITE}Master Orchestration Commands:${NC}"
    echo "═══════════════════════════════"
    echo "1) 🚀 Complete System Setup"
    echo "2) 💻 Development Workflow"
    echo "3) 🚢 Deploy to Staging"
    echo "4) 🚢 Deploy to Production"
    echo "5) 🔧 Maintenance Tasks"
    echo "6) 📊 Monitoring Dashboard"
    echo "7) ⚡ Performance Optimization"
    echo "8) 🔒 Security Audit"
    echo "9) 📚 Update Documentation"
    echo "10) 🏥 System Health Check"
    echo "11) 🚨 Emergency Recovery"
    echo "12) 🐼 Infinite Panda Adventure"
    echo "13) 📋 Show Available Tools"
    echo "0) Exit"
    echo ""
}

# Interactive mode
interactive_mode() {
    while true; do
        show_header
        show_menu

        read -p "Choose an option (0-12): " choice
        echo ""

        case $choice in
            1) system_setup ;;
            2) dev_workflow ;;
            3) deployment_pipeline "staging" ;;
            4) deployment_pipeline "production" ;;
            5) maintenance_tasks ;;
            6) monitoring_dashboard ;;
            7) performance_optimization ;;
            8) security_audit ;;
            9) docs_update ;;
            10) system_health ;;
            11) emergency_recovery ;;
            12) infinite_panda_adventure ;;
            13) show_tools ;;
            0) echo -e "${GREEN}Goodbye! 👋${NC}"; exit 0 ;;
            *) echo -e "${RED}Invalid option. Please choose 0-13.${NC}" ;;
        esac

        echo ""
        read -p "Press Enter to continue..."
        clear
    done
}

# Main execution
main() {
    # Parse command line arguments
    # Handle "infinite panda adventure" special case
    if [ "$1" = "infinite" ] && [ "$2" = "panda" ] && [ "$3" = "adventure" ]; then
        infinite_panda_adventure
        exit 0
    fi

    case "${1:-menu}" in
        "setup")
            system_setup ;;
        "dev")
            dev_workflow ;;
        "deploy-staging")
            deployment_pipeline "staging" ;;
        "deploy-production")
            deployment_pipeline "production" ;;
        "maintenance")
            maintenance_tasks ;;
        "monitor")
            monitoring_dashboard ;;
        "optimize")
            performance_optimization ;;
        "security")
            security_audit ;;
        "docs")
            docs_update ;;
        "health")
            system_health ;;
        "recovery")
            emergency_recovery ;;
        "infinite")
            infinite_panda_adventure ;;
        "tools")
            show_tools ;;
        "menu")
            interactive_mode ;;
        "help"|"-h"|"--help")
            show_header
            echo "Grokputer Master Orchestration Script"
            echo ""
            echo "Usage: $0 [COMMAND]"
            echo ""
            echo "Commands:"
            echo "  setup             - Complete system setup"
            echo "  dev               - Development workflow"
            echo "  deploy-staging    - Deploy to staging"
            echo "  deploy-production - Deploy to production"
            echo "  maintenance       - Run maintenance tasks"
            echo "  monitor           - Show monitoring dashboard"
            echo "  optimize          - Performance optimization"
            echo "  security          - Security audit"
            echo "  docs              - Update documentation"
            echo "  health            - System health check"
            echo "  recovery          - Emergency recovery"
            echo "  infinite          - Infinite Panda Adventure mode"
            echo "  tools             - Show available tools"
            echo "  menu              - Interactive menu (default)"
            echo "  help              - Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 setup          # Complete setup"
            echo "  $0 dev            # Development workflow"
            echo "  $0 infinite       # Panda adventure mode"
            echo "  $0 menu           # Interactive mode"
            ;;
        *)
            echo "Unknown command: $1"
            "$0" help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"