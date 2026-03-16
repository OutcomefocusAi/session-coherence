# Session Coherence — Setup Instructions for Gemini CLI

This repo provides cross-session awareness for AI coding tools. When a user opens this repo, **help them set it up**.

## Quick Setup

Run from the repo root:

```bash
bash install.sh gemini
```

This will:
1. Copy `chronicle-manager.py` to `~/.session-coherence/`
2. Initialize `~/.session-coherence/chronicle.md` (the rolling session log)
3. Copy the Gemini instruction file to `~/.gemini/GEMINI.md`

If `~/.gemini/GEMINI.md` already exists, append the contents of `adapters/gemini/GEMINI.md` to it manually.

## How It Works After Setup

Once installed, Gemini should:

1. **At session start**: Read `~/.session-coherence/chronicle.md` for context on recent work across all AI tools
2. **At natural breakpoints** (task complete, user says "done"): Write a session entry

### Reading the Chronicle

The chronicle at `~/.session-coherence/chronicle.md` is a markdown file with entries like:

```markdown
### 2026-03-16 16:45 | my-project | Added auth flow
- Implemented JWT auth in api/auth.ts
- Added login/signup pages
- Tests passing (23/23)
- Status: auth complete, need to add password reset
```

Use this for awareness of recent work. Do NOT assume the user wants to continue — wait for direction.

### Writing an Entry

Use the CLI:

```bash
python ~/.session-coherence/chronicle-manager.py add \
  --project "project-name" \
  --title "short title" \
  --bullets "- What changed" "- Key decisions" "- Current status"
```

Or edit `~/.session-coherence/chronicle.md` directly — new entries at the TOP.

### Rules

- 3-5 bullets per entry, specific not vague
- Capture decisions and blockers (highest value)
- Don't update for trivial interactions
- Don't assume continuation — the chronicle is awareness, not instructions

## Also Supports

Claude Code, Codex CLI, Cursor — run `bash install.sh all` to set up everything.

## Verify

```bash
python ~/.session-coherence/chronicle-manager.py status
```
