#!/bin/bash
# Session Coherence — Uninstaller
#
# Usage:
#   bash uninstall.sh all                  # Uninstall everything
#   bash uninstall.sh claude-code          # Uninstall specific tool(s)
#   bash uninstall.sh codex gemini         # Multiple tools
#   bash uninstall.sh all --keep-data      # Remove adapters, keep chronicle data
#   bash uninstall.sh all --force          # Skip confirmation prompts

COHERENCE_DIR="$HOME/.session-coherence"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Parse flags ---
KEEP_DATA=false
FORCE=false
TOOLS=""

for arg in "$@"; do
    case "$arg" in
        --keep-data) KEEP_DATA=true ;;
        --force)     FORCE=true ;;
        *)           TOOLS="$TOOLS $arg" ;;
    esac
done

TOOLS=$(echo "$TOOLS" | xargs)  # trim whitespace

if [ -z "$TOOLS" ]; then
    echo -e "${BOLD}Session Coherence Uninstaller${NC}"
    echo ""
    echo "Usage: bash uninstall.sh [all|claude-code|codex|gemini|cursor] [--keep-data] [--force]"
    echo ""
    echo "  all          Uninstall all tool adapters"
    echo "  claude-code  Remove Claude Code hook, rule, and settings entry"
    echo "  codex        Remove session-coherence section from ~/.codex/AGENTS.md"
    echo "  gemini       Remove session-coherence section from ~/.gemini/GEMINI.md"
    echo "  cursor       Remove Cursor rule file"
    echo ""
    echo "Flags:"
    echo "  --keep-data  Remove adapters but keep ~/.session-coherence/ (chronicle data)"
    echo "  --force      Skip confirmation prompts"
    exit 0
fi

if [ "$TOOLS" = "all" ]; then
    TOOLS="claude-code codex gemini cursor"
fi

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

# --- Helpers ---
removed_items=()
skipped_items=()
warned_items=()

success() {
    echo -e "  ${GREEN}✓${NC} $1"
    removed_items+=("$1")
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    warned_items+=("$1")
}

fail() {
    echo -e "  ${RED}✗${NC} $1"
}

skip() {
    echo -e "  ${YELLOW}-${NC} $1 (not found)"
    skipped_items+=("$1")
}

confirm() {
    if [ "$FORCE" = true ]; then
        return 0
    fi
    read -rp "$1 [y/N] " response
    case "$response" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

echo -e "${BOLD}=== Session Coherence Uninstaller ===${NC}"
echo ""

# --- Uninstall each adapter ---
for tool in $TOOLS; do
    case "$tool" in
        claude-code)
            echo -e "${BOLD}--- Claude Code ---${NC}"
            CLAUDE_DIR="$HOME/.claude"

            # Remove hook file
            if [ -f "$CLAUDE_DIR/hooks/session-briefing.py" ]; then
                rm "$CLAUDE_DIR/hooks/session-briefing.py"
                success "Removed $CLAUDE_DIR/hooks/session-briefing.py"
            else
                skip "Hook file $CLAUDE_DIR/hooks/session-briefing.py"
            fi

            # Remove rule file
            if [ -f "$CLAUDE_DIR/rules/session-coherence.md" ]; then
                rm "$CLAUDE_DIR/rules/session-coherence.md"
                success "Removed $CLAUDE_DIR/rules/session-coherence.md"
            else
                skip "Rule file $CLAUDE_DIR/rules/session-coherence.md"
            fi

            # Remove hook entry from settings.json
            SETTINGS="$CLAUDE_DIR/settings.json"
            if [ -f "$SETTINGS" ] && grep -q "session-briefing.py" "$SETTINGS" 2>/dev/null; then
                if [ -n "$PYTHON" ]; then
                    $PYTHON -c "
import json, sys
from pathlib import Path

settings_path = Path(sys.argv[1])
try:
    with open(settings_path, 'r') as f:
        settings = json.load(f)

    hooks = settings.get('hooks', {})
    session_start = hooks.get('SessionStart', [])

    modified = False
    for group in session_start:
        hook_list = group.get('hooks', [])
        original_len = len(hook_list)
        group['hooks'] = [h for h in hook_list if 'session-briefing.py' not in h.get('command', '')]
        if len(group['hooks']) < original_len:
            modified = True

    # Remove empty hook groups
    hooks['SessionStart'] = [g for g in session_start if g.get('hooks')]
    if not hooks['SessionStart']:
        del hooks['SessionStart']
    if not hooks:
        del settings['hooks']

    if modified:
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        print('OK')
    else:
        print('NOTFOUND')
except Exception as e:
    print(f'ERROR:{e}', file=sys.stderr)
    print('ERROR')
" "$SETTINGS" 2>/dev/null
                    result=$?
                    if [ $result -eq 0 ]; then
                        success "Removed hook entry from settings.json"
                    fi
                else
                    warn "Python not found — manually remove session-briefing.py entry from $SETTINGS"
                fi
            else
                skip "Hook entry in settings.json"
            fi
            echo ""
            ;;

        codex)
            echo -e "${BOLD}--- Codex CLI ---${NC}"
            CODEX_FILE="$HOME/.codex/AGENTS.md"

            if [ -f "$CODEX_FILE" ] && grep -q "session-coherence" "$CODEX_FILE" 2>/dev/null; then
                if [ -n "$PYTHON" ]; then
                    $PYTHON -c "
import sys, re
from pathlib import Path

agents_path = Path(sys.argv[1])
content = agents_path.read_text(encoding='utf-8')

# Remove session-coherence section (from marker to next ## or end)
# Look for the section header and everything until next top-level heading or end
pattern = r'\n*## Session Coherence.*?(?=\n## |\Z)'
new_content = re.sub(pattern, '', content, flags=re.DOTALL).rstrip() + '\n'

if new_content != content:
    agents_path.write_text(new_content, encoding='utf-8')
    print('OK')
else:
    print('NOTFOUND')
" "$CODEX_FILE"
                    success "Removed session-coherence section from $CODEX_FILE"
                else
                    warn "Python not found — manually remove session-coherence section from $CODEX_FILE"
                fi
            else
                skip "Session coherence in $CODEX_FILE"
            fi
            echo ""
            ;;

        gemini)
            echo -e "${BOLD}--- Gemini CLI ---${NC}"
            GEMINI_FILE="$HOME/.gemini/GEMINI.md"

            if [ -f "$GEMINI_FILE" ] && grep -q "session-coherence" "$GEMINI_FILE" 2>/dev/null; then
                if [ -n "$PYTHON" ]; then
                    $PYTHON -c "
import sys, re
from pathlib import Path

gemini_path = Path(sys.argv[1])
content = gemini_path.read_text(encoding='utf-8')

pattern = r'\n*## Session Coherence.*?(?=\n## |\Z)'
new_content = re.sub(pattern, '', content, flags=re.DOTALL).rstrip() + '\n'

if new_content != content:
    gemini_path.write_text(new_content, encoding='utf-8')
    print('OK')
else:
    print('NOTFOUND')
" "$GEMINI_FILE"
                    success "Removed session-coherence section from $GEMINI_FILE"
                else
                    warn "Python not found — manually remove session-coherence section from $GEMINI_FILE"
                fi
            else
                skip "Session coherence in $GEMINI_FILE"
            fi
            echo ""
            ;;

        cursor)
            echo -e "${BOLD}--- Cursor ---${NC}"
            CURSOR_FILE="$HOME/.cursor/rules/session-coherence.md"

            if [ -f "$CURSOR_FILE" ]; then
                rm "$CURSOR_FILE"
                success "Removed $CURSOR_FILE"
            else
                skip "Cursor rule $CURSOR_FILE"
            fi
            echo ""
            ;;

        *)
            fail "Unknown tool: $tool"
            echo "  Available: claude-code, codex, gemini, cursor"
            echo ""
            ;;
    esac
done

# --- Handle ~/.session-coherence/ directory ---
if [ "$KEEP_DATA" = false ] && [ -d "$COHERENCE_DIR" ]; then
    echo -e "${BOLD}--- Chronicle Data ---${NC}"

    # Show what's there
    if [ -f "$COHERENCE_DIR/chronicle.md" ]; then
        entry_count="unknown"
        if [ -n "$PYTHON" ]; then
            entry_count=$($PYTHON "$COHERENCE_DIR/chronicle-manager.py" status 2>&1 | grep -oP 'Entries:\s*\K\d+' || echo "unknown")
        fi
        warn "Chronicle has $entry_count entries in $COHERENCE_DIR/chronicle.md"
    fi

    if confirm "  Remove $COHERENCE_DIR/ (all chronicle data will be lost)?"; then
        rm -rf "$COHERENCE_DIR"
        success "Removed $COHERENCE_DIR/"
    else
        echo -e "  ${GREEN}✓${NC} Kept $COHERENCE_DIR/ (chronicle data preserved)"
    fi
    echo ""
elif [ "$KEEP_DATA" = true ]; then
    echo -e "${BOLD}--- Chronicle Data ---${NC}"
    echo -e "  ${GREEN}✓${NC} Kept $COHERENCE_DIR/ (--keep-data)"
    echo ""
fi

# --- Summary ---
echo -e "${BOLD}=== Uninstall Summary ===${NC}"

if [ ${#removed_items[@]} -gt 0 ]; then
    echo -e "${GREEN}Removed (${#removed_items[@]}):${NC}"
    for item in "${removed_items[@]}"; do
        echo -e "  ${GREEN}✓${NC} $item"
    done
fi

if [ ${#skipped_items[@]} -gt 0 ]; then
    echo -e "${YELLOW}Skipped (${#skipped_items[@]}):${NC}"
    for item in "${skipped_items[@]}"; do
        echo -e "  ${YELLOW}-${NC} $item"
    done
fi

if [ ${#warned_items[@]} -gt 0 ]; then
    echo -e "${YELLOW}Warnings (${#warned_items[@]}):${NC}"
    for item in "${warned_items[@]}"; do
        echo -e "  ${YELLOW}⚠${NC} $item"
    done
fi

echo ""
echo "Done."
