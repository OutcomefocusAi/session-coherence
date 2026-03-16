#!/bin/bash
# Install session-coherence for Codex CLI
# Run from the session-coherence repo root

set -e

COHERENCE_DIR="$HOME/.session-coherence"
CODEX_DIR="$HOME/.codex"

echo "Installing session-coherence for Codex CLI..."

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

# 3. Set up Codex instructions
mkdir -p "$CODEX_DIR"
if [ -f "$CODEX_DIR/AGENTS.md" ]; then
    echo ""
    echo "  WARNING: $CODEX_DIR/AGENTS.md already exists!"
    echo "  Append the session coherence protocol manually from:"
    echo "  adapters/codex/AGENTS.md"
else
    cp adapters/codex/AGENTS.md "$CODEX_DIR/AGENTS.md"
    echo "  Copied AGENTS.md -> $CODEX_DIR/"
fi

echo ""
echo "Done! Session coherence is ready for Codex CLI."
echo "Codex will read the chronicle from ~/.session-coherence/chronicle.md"
