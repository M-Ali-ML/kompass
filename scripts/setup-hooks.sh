#!/bin/bash

# Setup script to install git hooks

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

HOOK_SRC="scripts/pre-commit.sh"
HOOK_DEST=".git/hooks/pre-commit"

echo -e "${BLUE}Setting up git pre-commit hook...${NC}"

# Check if we are in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: .git directory not found. Are you in the root of the git repository?${NC}"
    exit 1
fi

# Ensure the scripts directory and pre-commit.sh exist
if [ ! -f "$HOOK_SRC" ]; then
    echo -e "${RED}Error: $HOOK_SRC not found.${NC}"
    exit 1
fi

# Copy the pre-commit hook to .git/hooks/
cp "$HOOK_SRC" "$HOOK_DEST"

# Make it executable
chmod +x "$HOOK_DEST"

echo -e "${GREEN}✓ Git pre-commit hook successfully installed at $HOOK_DEST!${NC}"
