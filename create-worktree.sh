#!/bin/bash
# Create a git worktree in sibling directory with project setup for Peaches Trading Bot

set -e

# Check for branch name argument
if [ $# -eq 0 ]; then
    echo "Usage: $0 <branch-name>"
    echo "Example: $0 feature/new-strategy"
    echo ""
    echo "This will create a worktree at: ../peaches-<branch-name>/"
    exit 1
fi

BRANCH_NAME="$1"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
PARENT_DIR="$(dirname "$PROJECT_ROOT")"

# Sanitize branch name for directory (replace / with -)
SAFE_BRANCH_NAME="${BRANCH_NAME//\//-}"
WORKTREE_PATH="$PARENT_DIR/$PROJECT_NAME-$SAFE_BRANCH_NAME"

# Check if worktree path already exists
if [ -d "$WORKTREE_PATH" ]; then
    echo "ERROR: Directory already exists: $WORKTREE_PATH"
    exit 1
fi

# Create the worktree with new branch
git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME"

cd "$WORKTREE_PATH"

# Initialize Python environment with uv (separate venv per worktree)
uv venv
uv sync --group dev

# Create symlinks for data and logs directories
ln -s /opt/peaches/data data-prod
ln -s /opt/peaches/logs logs-prod

# Copy .env from production
cp /opt/peaches/.env .env

# Copy pyrightconfig.json (already uses relative paths, no updates needed)
cp "$PROJECT_ROOT/pyrightconfig.json" pyrightconfig.json

# Copy opencode config and update venv path
mkdir -p .opencode
cp "$PROJECT_ROOT/.opencode/opencode.json" .opencode/
sed -i "s|$PROJECT_ROOT/\.venv|$WORKTREE_PATH/.venv|g" .opencode/opencode.json

# Ignore config changes in worktree
git update-index --assume-unchanged pyrightconfig.json
git update-index --assume-unchanged .opencode/opencode.json

echo "Worktree ready at: $WORKTREE_PATH"
echo ""
echo "To merge into main and clean up:"
echo "1. cd $PROJECT_ROOT && git merge $BRANCH_NAME"
echo "2. git worktree remove $WORKTREE_PATH"
echo "3. git branch -d $BRANCH_NAME"
echo ""

echo "Now cd into the worktree:"
echo "cd $WORKTREE_PATH"
