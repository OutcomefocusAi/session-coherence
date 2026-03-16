#!/bin/bash
# Install session-coherence for Claude Code
# Run from the session-coherence repo root

set -e

COHERENCE_DIR="$HOME/.session-coherence"
CLAUDE_DIR="$HOME/.claude"

echo "Installing session-coherence for Claude Code..."

# 1. Create shared directory and copy manager
mkdir -p "$COHERENCE_DIR"
cp chronicle-manager.py "$COHERENCE_DIR/chronicle-manager.py"
echo "  Copied chronicle-manager.py -> $COHERENCE_DIR/"

# 2. Initialize chronicle if not exists
if [ ! -f "$COHERENCE_DIR/chronicle.md" ]; then
    python "$COHERENCE_DIR/chronicle-manager.py" init
else
    echo "  Chronicle already exists, skipping init"
fi

# 3. Copy hook
cp adapters/claude-code/session-briefing.py "$CLAUDE_DIR/hooks/session-briefing.py"
echo "  Copied session-briefing.py -> $CLAUDE_DIR/hooks/"

# 4. Copy rule
cp adapters/claude-code/session-coherence.md "$CLAUDE_DIR/rules/session-coherence.md"
echo "  Copied session-coherence.md -> $CLAUDE_DIR/rules/"

# 5. Check settings.json for hook entry
if grep -q "session-briefing.py" "$CLAUDE_DIR/settings.json" 2>/dev/null; then
    echo "  Hook already registered in settings.json"
else
    echo ""
    echo "  NOTE: Add this to your settings.json SessionStart hooks:"
    echo '  {'
    echo '    "type": "command",'
    echo '    "command": "python \"'$CLAUDE_DIR'/hooks/session-briefing.py\"",'
    echo '    "timeout": 5'
    echo '  }'
fi

# 6. Migrate existing chronicle if present
OLD_CHRONICLE="$CLAUDE_DIR/session-chronicle.md"
if [ -f "$OLD_CHRONICLE" ] && [ ! -f "$COHERENCE_DIR/chronicle.md" ]; then
    cp "$OLD_CHRONICLE" "$COHERENCE_DIR/chronicle.md"
    echo "  Migrated existing chronicle from $OLD_CHRONICLE"
elif [ -f "$OLD_CHRONICLE" ] && [ -f "$COHERENCE_DIR/chronicle.md" ]; then
    echo "  NOTE: Old chronicle exists at $OLD_CHRONICLE — merge manually if needed"
fi

echo ""
echo "Done! Session coherence is ready for Claude Code."
echo "Run 'python $COHERENCE_DIR/chronicle-manager.py status' to verify."
