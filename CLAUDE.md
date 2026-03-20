# Session Coherence v2.0 — Setup for Claude Code

Cross-tool session memory for AI coding assistants. Zero dependencies, 9 tools supported.

## Quick Setup

```bash
bash install.sh claude-code
```

This will:
1. Copy `chronicle-manager.py` to `~/.session-coherence/`
2. Initialize `~/.session-coherence/chronicle.md`
3. Install the SessionStart hook to `~/.claude/hooks/session-briefing.py`
4. Install the coherence rule to `~/.claude/rules/session-coherence.md`
5. Auto-patch `~/.claude/settings.json` with the hook entry

## What It Does

- **Session start**: Hook generates a structured briefing (~300 tokens, one-time injection)
- **During session**: Claude writes summaries at natural breakpoints using semantic tags
- **Rotation**: Last 20 sessions kept (configurable), oldest archived (not deleted)
- **Plugins**: Extensible via `~/.session-coherence/plugins/` — add custom briefing hooks

## New in v2.0

- Archive system (rotated entries preserved, searchable)
- Full-text search across chronicle + archive
- Analytics (project stats, tag distribution, session frequency)
- JSON export, CSV export
- Config file (`~/.session-coherence/config.json`)
- File locking for safe concurrent writes
- Plugin system for briefing extensions
- Entry validation
- 9 tool adapters (Claude Code, Codex, Gemini, Cursor, Aider, Windsurf, Cline, Copilot, Zed)

## Verify

```bash
python ~/.session-coherence/chronicle-manager.py status
python ~/.session-coherence/chronicle-manager.py briefing
```

## Uninstall

```bash
bash uninstall.sh claude-code
```

## Also Supports

Codex CLI, Gemini CLI, Cursor, Aider, Windsurf, Cline, Copilot, Zed — run `bash install.sh all`
