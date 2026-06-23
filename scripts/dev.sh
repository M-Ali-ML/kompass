#!/bin/bash

# Get the project root directory (directory containing backend/ and frontend/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/dev.log"

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Kompass Dev Environment Startup ===${NC}"

port_in_use() {
    lsof -i :"$1" >/dev/null 2>&1
}

kill_port_owner() {
    local port=$1
    local pids
    pids=$(lsof -t -i :"$port")
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Port $port is in use by PID(s): $pids. Killing...${NC}"
        for pid in $pids; do
            kill "$pid" 2>/dev/null
        done
        sleep 1
        # If still in use, force kill
        if port_in_use "$port"; then
            echo -e "${RED}Port $port still in use. Force killing...${NC}"
            for pid in $pids; do
                kill -9 "$pid" 2>/dev/null
            done
            sleep 1
        fi
    fi
}

check_ports() {
    if port_in_use 8000; then
        echo -e "${YELLOW}Port 8000 (Backend) is in use. Attempting to free it...${NC}"
        kill_port_owner 8000
    fi
    if port_in_use 3000; then
        echo -e "${YELLOW}Port 3000 (Frontend) is in use. Attempting to free it...${NC}"
        kill_port_owner 3000
    fi
}

check_ports

# Clean up function
cleanup() {
    echo -e "\n${YELLOW}Stopping frontend and backend servers...${NC}"
    
    # Terminate backend and frontend if PIDs exist
    if [ -n "$BE_PID" ]; then
        kill "$BE_PID" 2>/dev/null
    fi
    if [ -n "$FE_PID" ]; then
        kill "$FE_PID" 2>/dev/null
    fi
    
    # Wait for processes to exit
    wait "$BE_PID" 2>/dev/null
    wait "$FE_PID" 2>/dev/null

    # Remove the log file if it exists
    if [ -f "$LOG_FILE" ]; then
        echo -e "${GREEN}Removing temp log file: dev.log${NC}"
        rm -f "$LOG_FILE"
    fi
    echo -e "${GREEN}Cleanup complete. Goodbye!${NC}"
    exit 0
}

# Trap SIGINT, SIGTERM, and EXIT
trap cleanup SIGINT SIGTERM EXIT

# Initialize log file
echo "=== Kompass Dev Session Started at $(date) ===" > "$LOG_FILE"

# Start Backend
echo -e "${BLUE}Starting Backend (uvicorn on port 8000)...${NC}"
cd "$PROJECT_ROOT/backend" || exit 1
uv run uvicorn app.main:app --reload >> "$LOG_FILE" 2>&1 &
BE_PID=$!

# Start Frontend
echo -e "${BLUE}Starting Frontend (Next.js on port 3000)...${NC}"
cd "$PROJECT_ROOT/frontend" || exit 1
npm run dev >> "$LOG_FILE" 2>&1 &
FE_PID=$!

echo -e "${GREEN}Both servers are starting up in the background.${NC}"
echo -e "Logs are being written to: ${YELLOW}$LOG_FILE${NC}"
echo -e "${BLUE}Streaming logs (Press Ctrl+C to stop servers and delete log file):${NC}"
echo "--------------------------------------------------------"

# Tail the log file to show output to the user
tail -n +1 -f "$LOG_FILE"
