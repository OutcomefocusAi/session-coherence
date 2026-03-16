#!/bin/bash
# Install session-coherence for Cursor
# Run from the session-coherence repo root

set -e

COHERENCE_DIR="$HOME/.session-coherence"

echo "Installing session-coherence for Cursor..."

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

# 3. Instructions for Cursor
echo ""
echo "  For Cursor, add the contents of adapters/cursor/cursorrules-snippet.md"
echo "  to your project's .cursorrules or ~/.cursor/rules/ file."
echo ""
echo "  Option A: Project-level (per repo)"
echo "    cat adapters/cursor/cursorrules-snippet.md >> /path/to/project/.cursorrules"
echo ""
echo "  Option B: Global (all projects)"
echo "    mkdir -p ~/.cursor/rules"
echo "    cp adapters/cursor/cursorrules-snippet.md ~/.cursor/rules/session-coherence.md"

echo ""
echo "Done! Session coherence is ready for Cursor."
