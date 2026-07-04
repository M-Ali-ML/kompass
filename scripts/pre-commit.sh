#!/bin/bash

# Pre-commit hook script
# Runs tests and lints for both frontend and backend.

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Running Pre-Commit Quality Checks   ${NC}"
echo -e "${BLUE}========================================${NC}"

# Track failures
FAILED=0

# Check 1: Frontend Lint
echo -e "\n${YELLOW}[1/3] Running Frontend Lints...${NC}"
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}frontend/node_modules not found. Running npm install...${NC}"
    (cd frontend && npm install)
fi

if cd frontend && npm run lint; then
    echo -e "${GREEN}✓ Frontend lints passed!${NC}"
else
    echo -e "${RED}✗ Frontend lints failed!${NC}"
    FAILED=1
fi
cd - > /dev/null

# Check 2: Frontend Unit Tests
echo -e "\n${YELLOW}[2/3] Running Frontend Unit Tests...${NC}"
if cd frontend && npm run test:unit; then
    echo -e "${GREEN}✓ Frontend unit tests passed!${NC}"
else
    echo -e "${RED}✗ Frontend unit tests failed!${NC}"
    FAILED=1
fi
cd - > /dev/null

# Check 3: Backend Tests
echo -e "\n${YELLOW}[3/3] Running Backend Tests...${NC}"
if ! command -v uv &> /dev/null; then
    echo -e "${RED}✗ uv command not found. Please install uv to run backend tests.${NC}"
    FAILED=1
else
    if cd backend && uv run pytest; then
        echo -e "${GREEN}✓ Backend tests passed!${NC}"
    else
        echo -e "${RED}✗ Backend tests failed!${NC}"
        FAILED=1
    fi
    cd - > /dev/null
fi

echo -e "\n${BLUE}========================================${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Commit allowed.${NC}"
    echo -e "${BLUE}========================================${NC}"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please fix the issues before committing.${NC}"
    echo -e "${BLUE}========================================${NC}"
    exit 1
fi
