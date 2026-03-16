#!/bin/bash
# Session Coherence — Global Installer
# Installs the shared chronicle-manager and sets up selected tool adapters.
#
# Usage:
#   ./install.sh                    # Interactive — asks which tools
#   ./install.sh claude-code        # Install for Claude Code only
#   ./install.sh codex gemini       # Install for Codex + Gemini
#   ./install.sh all                # Install all adapters

set -e

COHERENCE_DIR="$HOME/.session-coherence"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Session Coherence Installer ==="
echo ""

# 1. Install shared core
echo "Installing shared core..."
mkdir -p "$COHERENCE_DIR"
cp "$SCRIPT_DIR/chronicle-manager.py" "$COHERENCE_DIR/chronicle-manager.py"
echo "  chronicle-manager.py -> $COHERENCE_DIR/"

# Initialize chronicle if not exists
if [ ! -f "$COHERENCE_DIR/chronicle.md" ]; then
    python "$COHERENCE_DIR/chronicle-manager.py" init
else
    echo "  Chronicle already exists ($(python "$COHERENCE_DIR/chronicle-manager.py" status 2>&1 | grep Entries))"
fi

echo ""

# 2. Determine which adapters to install
TOOLS="$@"

if [ -z "$TOOLS" ]; then
    echo "Which tools do you use? (space-separated, or 'all')"
    echo "  Available: claude-code, codex, gemini, cursor"
    read -r TOOLS
fi

if [ "$TOOLS" = "all" ]; then
    TOOLS="claude-code codex gemini cursor"
fi

# 3. Install each adapter
for tool in $TOOLS; do
    echo ""
    adapter_dir="$SCRIPT_DIR/adapters/$tool"
    if [ -d "$adapter_dir" ] && [ -f "$adapter_dir/install.sh" ]; then
        echo "--- Installing $tool adapter ---"
        cd "$SCRIPT_DIR"
        bash "$adapter_dir/install.sh"
    else
        echo "  Unknown tool: $tool (no adapter found at $adapter_dir)"
    fi
done

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Chronicle: $COHERENCE_DIR/chronicle.md"
echo "Manager:   $COHERENCE_DIR/chronicle-manager.py"
echo ""
echo "Quick commands:"
echo "  python $COHERENCE_DIR/chronicle-manager.py status"
echo "  python $COHERENCE_DIR/chronicle-manager.py briefing"
echo "  python $COHERENCE_DIR/chronicle-manager.py add --project X --title Y --bullets \"- item\""
