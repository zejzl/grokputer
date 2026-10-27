#!/bin/bash
# Panda Save Game System
# Auto-save daemon for infinite panda adventures

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}🐼 Panda Save Game System 🐼${NC}"
echo "==========================="

# Save game directory
SAVE_DIR="saves/panda_adventure"
PID_FILE="$SAVE_DIR/daemon.pid"
SAVE_FILE="$SAVE_DIR/panda_save.json"
LOG_FILE="$SAVE_DIR/panda_daemon.log"

# Create save directory
mkdir -p "$SAVE_DIR"

# Function to save panda game state
save_panda_game() {
    local cycle="$1"
    local achievements="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Create save data
    cat > "$SAVE_FILE.tmp" << EOF
{
  "save_version": "1.0",
  "timestamp": "$timestamp",
  "cycle": $cycle,
  "achievements": $achievements,
  "system_health": {
    "docker_running": $(docker ps 2>/dev/null | grep -q grokputer && echo true || echo false),
    "redis_backup_exists": $([ -f "vault/redis_backup.json" ] && echo true || echo false),
    "reports_count": $(find reports/ -name "*.txt" -o -name "*.md" 2>/dev/null | wc -l),
    "env_configured": $([ -f ".env" ] && echo true || echo false)
  },
  "panda_stats": {
    "automation_level": $((cycle / 10 + 1)),
    "bamboo_collected": $((cycle * 42)),
    "meditations_completed": $((cycle / 5)),
    "enlightenment_progress": $((achievements * 25))
  },
  "last_save_location": "cycle_$cycle"
}
EOF

    # Atomic save
    mv "$SAVE_FILE.tmp" "$SAVE_FILE"

    echo "$(date '+%Y-%m-%d %H:%M:%S') [SAVE] Game saved at cycle $cycle (achievements: $achievements)" >> "$LOG_FILE"
}

# Function to load panda game state
load_panda_game() {
    if [ -f "$SAVE_FILE" ]; then
        echo -e "${GREEN}🐼 Loading saved panda adventure...${NC}"

        # Parse save data
        local cycle
        local achievements
        cycle=$(grep '"cycle"' "$SAVE_FILE" | sed 's/.*: \([0-9]*\).*/\1/')
        achievements=$(grep '"achievements"' "$SAVE_FILE" | sed 's/.*: \([0-9]*\).*/\1/')

        echo -e "${CYAN}Resuming from cycle: $cycle${NC}"
        echo -e "${CYAN}Achievements unlocked: $achievements${NC}"

        # Return values
        echo "$cycle $achievements"
    else
        echo -e "${YELLOW}🐼 No saved game found. Starting fresh adventure!${NC}"
        echo "1 0"  # Default: cycle 1, 0 achievements
    fi
}

# Function to start auto-save daemon
start_auto_save_daemon() {
    local interval="${1:-25}"  # Default 25 cycles

    echo -e "${PURPLE}🐼 Starting Panda Auto-Save Daemon (every $interval cycles)...${NC}"

    # Check if daemon is already running
    if [ -f "$PID_FILE" ]; then
        local existing_pid
        existing_pid=$(cat "$PID_FILE")
        if kill -0 "$existing_pid" 2>/dev/null; then
            echo -e "${YELLOW}🐼 Auto-save daemon already running (PID: $existing_pid)${NC}"
            return 0
        else
            echo -e "${YELLOW}🐼 Cleaning up stale PID file${NC}"
            rm -f "$PID_FILE"
        fi
    fi

    # Start daemon in background
    (
        echo "$(date '+%Y-%m-%d %H:%M:%S') [DAEMON] Panda auto-save daemon started (interval: $interval cycles)" >> "$LOG_FILE"

        local cycle=1
        local achievements=0

        while true; do
            # Wait for save signal or check periodically
            if [ -f "$SAVE_DIR/save_signal" ]; then
                # Read save data from signal file
                local save_data
                save_data=$(cat "$SAVE_DIR/save_signal")
                cycle=$(echo "$save_data" | cut -d' ' -f1)
                achievements=$(echo "$save_data" | cut -d' ' -f2)

                # Save the game
                save_panda_game "$cycle" "$achievements"

                # Remove signal file
                rm -f "$SAVE_DIR/save_signal"

                echo "$(date '+%Y-%m-%d %H:%M:%S') [DAEMON] Auto-saved at cycle $cycle" >> "$LOG_FILE"
            fi

            sleep 1  # Check every second
        done
    ) &

    local daemon_pid=$!
    echo $daemon_pid > "$PID_FILE"

    echo -e "${GREEN}🐼 Auto-save daemon started! (PID: $daemon_pid)${NC}"
    echo -e "${BLUE}Save files: $SAVE_DIR${NC}"
}

# Function to stop auto-save daemon
stop_auto_save_daemon() {
    if [ -f "$PID_FILE" ]; then
        local daemon_pid
        daemon_pid=$(cat "$PID_FILE")

        if kill -0 "$daemon_pid" 2>/dev/null; then
            echo -e "${YELLOW}🐼 Stopping auto-save daemon (PID: $daemon_pid)...${NC}"
            kill "$daemon_pid"
            wait "$daemon_pid" 2>/dev/null || true
            echo -e "${GREEN}🐼 Auto-save daemon stopped${NC}"
        else
            echo -e "${YELLOW}🐼 Daemon process not found${NC}"
        fi

        rm -f "$PID_FILE"
    else
        echo -e "${YELLOW}🐼 No auto-save daemon running${NC}"
    fi
}

# Function to trigger manual save
trigger_save() {
    local cycle="$1"
    local achievements="$2"

    if [ -f "$PID_FILE" ]; then
        # Send save signal to daemon
        echo "$cycle $achievements" > "$SAVE_DIR/save_signal"
        echo -e "${GREEN}🐼 Save signal sent to daemon${NC}"
    else
        # Save directly if no daemon
        save_panda_game "$cycle" "$achievements"
        echo -e "${GREEN}🐼 Game saved directly${NC}"
    fi
}

# Function to show save game status
show_save_status() {
    echo -e "${CYAN}🐼 Panda Save Game Status${NC}"
    echo "==========================="

    if [ -f "$SAVE_FILE" ]; then
        echo -e "${GREEN}✓ Save file exists: $SAVE_FILE${NC}"

        # Show save info
        local timestamp cycle achievements
        timestamp=$(grep '"timestamp"' "$SAVE_FILE" | sed 's/.*: "\([^"]*\)".*/\1/')
        cycle=$(grep '"cycle"' "$SAVE_FILE" | sed 's/.*: \([0-9]*\).*/\1/')
        achievements=$(grep '"achievements"' "$SAVE_FILE" | sed 's/.*: \([0-9]*\).*/\1/')

        echo "Last saved: $timestamp"
        echo "Cycle: $cycle"
        echo "Achievements: $achievements"

        # Show panda stats
        local automation_level bamboo_collected
        automation_level=$(grep '"automation_level"' "$SAVE_FILE" | sed 's/.*: \([0-9]*\).*/\1/')
        bamboo_collected=$(grep '"bamboo_collected"' "$SAVE_FILE" | sed 's/.*: \([0-9]*\).*/\1/')

        echo ""
        echo -e "${PURPLE}🐼 Panda Stats:${NC}"
        echo "Automation Level: $automation_level"
        echo "Bamboo Collected: $bamboo_collected"
    else
        echo -e "${YELLOW}⚠ No save file found${NC}"
    fi

    echo ""
    if [ -f "$PID_FILE" ]; then
        local daemon_pid
        daemon_pid=$(cat "$PID_FILE")
        echo -e "${GREEN}✓ Auto-save daemon running (PID: $daemon_pid)${NC}"
    else
        echo -e "${YELLOW}⚠ Auto-save daemon not running${NC}"
    fi

    if [ -f "$LOG_FILE" ]; then
        echo -e "${GREEN}✓ Daemon log available: $LOG_FILE${NC}"
        echo "Recent activity:"
        tail -3 "$LOG_FILE" 2>/dev/null || echo "No recent activity"
    fi
}

# Function to list all save files
list_saves() {
    echo -e "${CYAN}🐼 Available Panda Save Files${NC}"
    echo "==============================="

    if [ -d "$SAVE_DIR" ]; then
        find "$SAVE_DIR" -name "*.json" -type f | while read -r save_file; do
            local filename
            filename=$(basename "$save_file")

            if [ -f "$save_file" ]; then
                local timestamp cycle
                timestamp=$(grep '"timestamp"' "$save_file" | sed 's/.*: "\([^"]*\)".*/\1/' | head -1)
                cycle=$(grep '"cycle"' "$save_file" | sed 's/.*: \([0-9]*\).*/\1/' | head -1)

                echo -e "${GREEN}📁 $filename${NC}"
                echo "   Saved: $timestamp"
                echo "   Cycle: $cycle"
                echo ""
            fi
        done
    else
        echo -e "${YELLOW}No save directory found${NC}"
    fi
}

# Function to backup save files
backup_saves() {
    local backup_file="backups/panda_saves_$(date +%Y%m%d_%H%M%S).tar.gz"

    if [ -d "$SAVE_DIR" ]; then
        mkdir -p backups
        tar -czf "$backup_file" -C saves panda_adventure/
        echo -e "${GREEN}🐼 Panda saves backed up to: $backup_file${NC}"
    else
        echo -e "${YELLOW}🐼 No panda saves to backup${NC}"
    fi
}

# Main execution
case "${1:-status}" in
    "start")
        start_auto_save_daemon "${2:-25}" ;;
    "stop")
        stop_auto_save_daemon ;;
    "save")
        trigger_save "${2:-1}" "${3:-0}" ;;
    "load")
        load_panda_game ;;
    "status")
        show_save_status ;;
    "list")
        list_saves ;;
    "backup")
        backup_saves ;;
    "clean")
        echo -e "${YELLOW}🐼 Cleaning panda save files...${NC}"
        rm -rf "$SAVE_DIR"
        echo -e "${GREEN}✓ Panda saves cleaned${NC}" ;;
    "help"|"-h"|"--help")
        echo "Panda Save Game System"
        echo ""
        echo "Usage: $0 [COMMAND] [OPTIONS]"
        echo ""
        echo "Commands:"
        echo "  start [interval]  - Start auto-save daemon (default: 25 cycles)"
        echo "  stop              - Stop auto-save daemon"
        echo "  save [cycle] [achievements] - Trigger manual save"
        echo "  load              - Load saved game state"
        echo "  status            - Show save game status"
        echo "  list              - List all save files"
        echo "  backup            - Backup save files"
        echo "  clean             - Clean all save files"
        echo "  help              - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 start 25       # Start daemon saving every 25 cycles"
        echo "  $0 save 42 3      # Save at cycle 42 with 3 achievements"
        echo "  $0 status         # Show current save status"
        ;;
    *)
        echo "Unknown command: $1"
        "$0" help
        exit 1
        ;;
esac

echo -e "${GREEN}🐼 Panda save game system operation completed!${NC}"