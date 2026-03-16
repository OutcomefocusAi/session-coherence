#!/bin/bash
# Session Coherence — Global Installer
#
# Usage:
#   ./install.sh                    # Interactive — asks which tools
#   ./install.sh claude-code        # Install for specific tool(s)
#   ./install.sh codex gemini       # Multiple tools
#   ./install.sh all                # Everything

set -e

COHERENCE_DIR="$HOME/.session-coherence"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Detect Python ---
PYTHON=""
for cmd in python3 python py; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | head -1)
        if echo "$version" | grep -qE "Python 3\.[8-9]|Python 3\.[1-9][0-9]"; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.8+ is required but not found."
    echo "Install Python from https://python.org and try again."
    exit 1
fi

echo "=== Session Coherence Installer ==="
echo "Python: $PYTHON ($($PYTHON --version 2>&1))"
echo ""

# --- Install shared core ---
echo "Installing shared core..."
mkdir -p "$COHERENCE_DIR"
cp "$SCRIPT_DIR/chronicle-manager.py" "$COHERENCE_DIR/chronicle-manager.py"
echo "  chronicle-manager.py -> $COHERENCE_DIR/"

if [ ! -f "$COHERENCE_DIR/chronicle.md" ]; then
    $PYTHON "$COHERENCE_DIR/chronicle-manager.py" init
else
    entries=$($PYTHON "$COHERENCE_DIR/chronicle-manager.py" status 2>&1 | grep "Entries:" || echo "Entries: ?")
    echo "  Chronicle already exists ($entries)"
fi

echo ""

# --- Determine tools ---
TOOLS="$@"

if [ -z "$TOOLS" ]; then
    echo "Which tools do you use? (space-separated, or 'all')"
    echo "  Available: claude-code  codex  gemini  cursor"
    echo ""
    read -rp "> " TOOLS
    echo ""
fi

if [ "$TOOLS" = "all" ]; then
    TOOLS="claude-code codex gemini cursor"
fi

# --- Install each adapter ---
for tool in $TOOLS; do
    case "$tool" in
        claude-code)
            echo "--- Claude Code ---"
            CLAUDE_DIR="$HOME/.claude"
            mkdir -p "$CLAUDE_DIR/hooks" "$CLAUDE_DIR/rules"

            cp "$SCRIPT_DIR/adapters/claude-code/session-briefing.py" "$CLAUDE_DIR/hooks/session-briefing.py"
            echo "  Hook -> $CLAUDE_DIR/hooks/session-briefing.py"

            cp "$SCRIPT_DIR/adapters/claude-code/session-coherence.md" "$CLAUDE_DIR/rules/session-coherence.md"
            echo "  Rule -> $CLAUDE_DIR/rules/session-coherence.md"

            # Auto-patch settings.json
            SETTINGS="$CLAUDE_DIR/settings.json"
            if [ -f "$SETTINGS" ]; then
                if grep -q "session-briefing.py" "$SETTINGS" 2>/dev/null; then
                    echo "  Hook already registered in settings.json"
                else
                    # Resolve home dir for the hook command path
                    HOOK_PATH="$CLAUDE_DIR/hooks/session-briefing.py"
                    # Convert to forward slashes for JSON
                    HOOK_PATH_JSON=$(echo "$HOOK_PATH" | sed 's|\\|/|g')

                    # Use Python to safely patch the JSON
                    $PYTHON -c "
import json, sys
from pathlib import Path

settings_path = Path('$SETTINGS'.replace('\\\\', '/'))
hook_path = '$HOOK_PATH_JSON'

try:
    with open(settings_path, 'r') as f:
        settings = json.load(f)

    hooks = settings.setdefault('hooks', {})
    session_start = hooks.setdefault('SessionStart', [{'hooks': []}])

    # Find the hooks array
    hook_list = session_start[0].setdefault('hooks', [])

    # Add our hook
    hook_list.append({
        'type': 'command',
        'command': f'python \"{hook_path}\"',
        'timeout': 5
    })

    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)

    print('  Auto-patched settings.json with SessionStart hook')
except Exception as e:
    print(f'  WARNING: Could not auto-patch settings.json: {e}')
    print(f'  Manually add session-briefing.py to SessionStart hooks')
"
                fi
            else
                echo "  WARNING: No settings.json found at $SETTINGS"
                echo "  Create one or manually add the SessionStart hook"
            fi
            echo ""
            ;;

        codex)
            echo "--- Codex CLI ---"
            CODEX_DIR="$HOME/.codex"
            mkdir -p "$CODEX_DIR"

            if [ -f "$CODEX_DIR/AGENTS.md" ]; then
                if grep -q "session-coherence" "$CODEX_DIR/AGENTS.md" 2>/dev/null; then
                    echo "  Session coherence already in AGENTS.md"
                else
                    echo "" >> "$CODEX_DIR/AGENTS.md"
                    cat "$SCRIPT_DIR/adapters/codex/AGENTS.md" >> "$CODEX_DIR/AGENTS.md"
                    echo "  Appended session coherence protocol to $CODEX_DIR/AGENTS.md"
                fi
            else
                cp "$SCRIPT_DIR/adapters/codex/AGENTS.md" "$CODEX_DIR/AGENTS.md"
                echo "  Created $CODEX_DIR/AGENTS.md"
            fi
            echo ""
            ;;

        gemini)
            echo "--- Gemini CLI ---"
            GEMINI_DIR="$HOME/.gemini"
            mkdir -p "$GEMINI_DIR"

            if [ -f "$GEMINI_DIR/GEMINI.md" ]; then
                if grep -q "session-coherence" "$GEMINI_DIR/GEMINI.md" 2>/dev/null; then
                    echo "  Session coherence already in GEMINI.md"
                else
                    echo "" >> "$GEMINI_DIR/GEMINI.md"
                    cat "$SCRIPT_DIR/adapters/gemini/GEMINI.md" >> "$GEMINI_DIR/GEMINI.md"
                    echo "  Appended session coherence protocol to $GEMINI_DIR/GEMINI.md"
                fi
            else
                cp "$SCRIPT_DIR/adapters/gemini/GEMINI.md" "$GEMINI_DIR/GEMINI.md"
                echo "  Created $GEMINI_DIR/GEMINI.md"
            fi
            echo ""
            ;;

        cursor)
            echo "--- Cursor ---"
            CURSOR_DIR="$HOME/.cursor/rules"
            mkdir -p "$CURSOR_DIR"

            if [ -f "$CURSOR_DIR/session-coherence.md" ]; then
                echo "  Session coherence rule already exists"
            else
                cp "$SCRIPT_DIR/adapters/cursor/cursorrules-snippet.md" "$CURSOR_DIR/session-coherence.md"
                echo "  Created $CURSOR_DIR/session-coherence.md"
            fi
            echo ""
            ;;

        *)
            echo "  Unknown tool: $tool"
            echo "  Available: claude-code, codex, gemini, cursor"
            echo ""
            ;;
    esac
done

# --- Summary ---
echo "=== Installation Complete ==="
echo ""
echo "Chronicle: $COHERENCE_DIR/chronicle.md"
echo "Manager:   $COHERENCE_DIR/chronicle-manager.py"
echo ""
echo "Verify:"
echo "  $PYTHON $COHERENCE_DIR/chronicle-manager.py status"
echo "  $PYTHON $COHERENCE_DIR/chronicle-manager.py briefing"
