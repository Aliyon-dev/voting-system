#!/bin/bash

# E-Voting System Startup Script
# This script starts the Django backend server

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  E-Voting System Startup (Django Only)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not found. Creating one...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created!${NC}"
    echo -e "${YELLOW}Please run: source venv/bin/activate && pip install -r requirements.txt${NC}"
    echo -e "${YELLOW}Then run this script again.${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if Django dependencies are installed
if ! python -c "import django" 2>/dev/null; then
    echo -e "${YELLOW}Django not found. Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Check if migrations are up to date
echo -e "${GREEN}Checking database migrations...${NC}"
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Start Django backend
echo -e "${GREEN}Starting Django backend server...${NC}"
export DEBUG=True
# Run in foreground to see logs easily, or background if we want to keep the script running for other reasons.
# The original script ran it in background and waited. For a single service, running in foreground is usually fine,
# but since the original had a trap/cleanup, I'll keep the background run style for consistency and control.
python manage.py runserver &
DJANGO_PID=$!

# Wait a moment for Django to start
sleep 2

# Check if Django started successfully
if ! kill -0 $DJANGO_PID 2>/dev/null; then
    echo -e "${YELLOW}Django server failed to start.${NC}"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down server...${NC}"
    kill $DJANGO_PID 2>/dev/null
    echo -e "${GREEN}Server stopped.${NC}"
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Django server is running!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Access the site at:${NC} http://localhost:8000"
echo -e "${GREEN}Admin Panel:${NC}        http://localhost:8000/admin"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Wait for user interrupt
wait
