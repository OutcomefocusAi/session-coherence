# Session Coherence v2.0 — Setup for Codex CLI

Cross-tool session memory for AI coding assistants. Zero dependencies, 9 tools supported.

## Quick Setup

```bash
bash install.sh codex
```

This will:
1. Copy `chronicle-manager.py` to `~/.session-coherence/`
2. Initialize `~/.session-coherence/chronicle.md`
3. Append session coherence protocol to `~/.codex/AGENTS.md`

## How It Works

**At session start**: Read `~/.session-coherence/chronicle.md` for context on recent work across all AI tools. Do NOT assume continuation — wait for direction.

**At breakpoints** (task complete, user says "done"): Write an entry:

```bash
python ~/.session-coherence/chronicle-manager.py add \
  --project "project-name" \
  --title "short title" \
  --bullets "- What changed" \
           "- [decision] Key choice and reasoning" \
           "- [status] Current state" \
           "- [next] Follow-up needed"
```

## Semantic Tags

| Tag | Purpose |
|-----|---------|
| `[change]` | What was modified (default) |
| `[decision]` | Choices made with reasoning |
| `[blocker]` | What's stuck |
| `[status]` | Current project state |
| `[next]` | Immediate follow-up |
| `[priority]` | Top focus item |

## CLI

```bash
python ~/.session-coherence/chronicle-manager.py status      # Check state
python ~/.session-coherence/chronicle-manager.py briefing    # Generate briefing
python ~/.session-coherence/chronicle-manager.py search "X"  # Search history
python ~/.session-coherence/chronicle-manager.py analytics   # Session stats
```

## Also Supports

Claude Code, Gemini CLI, Cursor, Aider, Windsurf, Cline, Copilot, Zed — run `bash install.sh all`
