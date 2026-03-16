# Session Coherence — Setup Instructions for Claude Code

This repo provides cross-session awareness for AI coding tools. When a user clones this repo and opens it in Claude Code, **run the setup automatically**.

## Quick Setup

Run this from the repo root:

```bash
bash install.sh claude-code
```

This will:
1. Copy `chronicle-manager.py` to `~/.session-coherence/`
2. Initialize `~/.session-coherence/chronicle.md` (the rolling session log)
3. Copy the SessionStart hook to `~/.claude/hooks/session-briefing.py`
4. Copy the coherence rule to `~/.claude/rules/session-coherence.md`

## Manual Step Required

After running the installer, add this hook entry to `~/.claude/settings.json` inside the `hooks.SessionStart[0].hooks` array:

```json
{
  "type": "command",
  "command": "python \"~/.claude/hooks/session-briefing.py\"",
  "timeout": 5
}
```

Replace `~` with the actual home directory path (e.g., `C:/Users/username` on Windows, `/home/username` on Linux/Mac).

The installer will tell you if this is already configured.

## What It Does

- **Session start**: Hook reads `~/.session-coherence/chronicle.md`, injects a ~300 token briefing into context (one-time, no per-prompt injection)
- **During session**: Claude follows the rule in `session-coherence.md` to write session summaries at natural breakpoints (task complete, before `/clear`, user says "done")
- **Rotation**: Last 20 sessions kept, oldest auto-trimmed

## If Setup Has Issues

- **Python not found**: The scripts need Python 3.8+. On Windows, try `py` instead of `python` — update the hook command in settings.json accordingly.
- **Permissions**: The hook must exit 0 always. It's built to never block session start.
- **Qdrant guards**: The Claude Code adapter optionally pulls guard memories from local Qdrant (port 6333). This is optional — if Qdrant isn't running, it's silently skipped.

## Verify

```bash
python ~/.session-coherence/chronicle-manager.py status
```
