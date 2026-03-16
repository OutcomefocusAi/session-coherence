#!/bin/bash
# Install session-coherence for Gemini CLI
# Run from the session-coherence repo root

set -e

COHERENCE_DIR="$HOME/.session-coherence"
GEMINI_DIR="$HOME/.gemini"

echo "Installing session-coherence for Gemini CLI..."

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

# 3. Set up Gemini instructions
mkdir -p "$GEMINI_DIR"
if [ -f "$GEMINI_DIR/GEMINI.md" ]; then
    echo ""
    echo "  WARNING: $GEMINI_DIR/GEMINI.md already exists!"
    echo "  Append the session coherence protocol manually from:"
    echo "  adapters/gemini/GEMINI.md"
else
    cp adapters/gemini/GEMINI.md "$GEMINI_DIR/GEMINI.md"
    echo "  Copied GEMINI.md -> $GEMINI_DIR/"
fi

echo ""
echo "Done! Session coherence is ready for Gemini CLI."
echo "Gemini will read the chronicle from ~/.session-coherence/chronicle.md"
