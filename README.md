# Session Coherence

Cross-session awareness for AI coding tools. Each new session knows what you were working on — without context bloat.

Works with **Claude Code**, **Codex CLI**, **Gemini CLI**, and **Cursor**.

## The Problem

Every new AI coding session starts cold. You re-explain which repo, what you were doing, what decisions were made. Context windows grow if you try to load everything.

## The Solution

A rolling session chronicle — a single markdown file shared across all your AI tools:

- **Fixed cost**: ~300 tokens at session start, never grows mid-session
- **Rolling window**: Last 20 sessions, oldest auto-trimmed
- **Cross-tool**: All tools read/write the same file
- **Not assumptive**: Shows recent work as context, doesn't assume continuation

## Setup

### Requirements

- Python 3.8+ (stdlib only, no pip dependencies)
- One or more supported AI tools

### Install

```bash
git clone https://github.com/OutcomefocusAi/session-coherence.git
cd session-coherence
bash install.sh all          # Install for all tools
```

Or pick specific tools:

```bash
bash install.sh claude-code          # Claude Code only
bash install.sh codex gemini         # Codex + Gemini
bash install.sh cursor               # Cursor only
```

The installer:
1. Copies `chronicle-manager.py` to `~/.session-coherence/`
2. Initializes the chronicle file at `~/.session-coherence/chronicle.md`
3. Installs the adapter for each selected tool (hooks, rules, instruction files)
4. Auto-patches `settings.json` for Claude Code (no manual JSON editing)

### What Gets Installed Per Tool

| Tool | What's Installed | How It Works |
|------|-----------------|-------------|
| **Claude Code** | Hook (`~/.claude/hooks/session-briefing.py`) + Rule (`~/.claude/rules/session-coherence.md`) + settings.json entry | Hook auto-injects briefing at session start. Rule tells Claude when to write entries. |
| **Codex CLI** | Instructions appended to `~/.codex/AGENTS.md` | Codex reads chronicle when instructed. Writes entries at breakpoints. |
| **Gemini CLI** | Instructions appended to `~/.gemini/GEMINI.md` | Gemini reads chronicle when instructed. Writes entries at breakpoints. |
| **Cursor** | Rule at `~/.cursor/rules/session-coherence.md` | Cursor reads chronicle when instructed. Writes entries at breakpoints. |

### Verify

```bash
python ~/.session-coherence/chronicle-manager.py status
python ~/.session-coherence/chronicle-manager.py briefing
```

## How It Works

```
Session Start                    During Session                Session End
┌─────────────┐                 ┌──────────────┐             ┌─────────────┐
│ Read         │                 │ No auto-     │             │ Write 3-5   │
│ chronicle    │──> ~300 token   │ injection    │             │ bullet      │──> chronicle
│ (last 20     │    briefing     │ Zero cost    │             │ summary     │    updated
│  sessions)   │    (one-time)   │ mid-session  │             │             │
└─────────────┘                 └──────────────┘             └─────────────┘
```

### Example Briefing (what you see at session start)

```
## Session Briefing

Recent work:
- Mar 16 | outcome-focus | M2 webhook fix
  > Fixed Stripe retry logic in api/webhooks/stripe.ts
  > Decision: exponential backoff for M3. M3 planning next.
- Mar 15 | claude-voice | PTT investigation
  > Root cause: edge-tts timeout. Blocked, needs async keep-alive.
- Mar 14 | new-saas-project | Project initialization
  > Ran /gsd:new-project, set up React + Supabase stack

Active projects: outcome-focus (M2 done, M3 next), claude-voice (PTT blocked)
```

### Example Chronicle Entry (what gets written)

```markdown
### 2026-03-16 16:45 | outcome-focus | M2 webhook fix
- Fixed Stripe webhook retry in api/webhooks/stripe.ts (silent failure after 3rd retry)
- Updated error handling to surface failures to dashboard
- All M2 tests passing (147/147)
- Decision: exponential backoff for M3 retry strategy
- Status: M2 complete, M3 planning next
```

## CLI Reference

```bash
# Check status
python ~/.session-coherence/chronicle-manager.py status

# Generate briefing (what the session start hook shows)
python ~/.session-coherence/chronicle-manager.py briefing

# Add a session entry (auto-rotates if > 20 entries)
python ~/.session-coherence/chronicle-manager.py add \
  --project "my-app" \
  --title "Added auth flow" \
  --bullets "- Implemented JWT auth in api/auth.ts" \
           "- Added login/signup pages" \
           "- Tests passing (23/23)" \
           "- Status: auth complete, need password reset next"

# Manually rotate (usually not needed — add auto-rotates)
python ~/.session-coherence/chronicle-manager.py rotate --max-entries 20

# Initialize fresh (first time only)
python ~/.session-coherence/chronicle-manager.py init
```

## Architecture

```
~/.session-coherence/               ← Shared by all tools
├── chronicle.md                    ← The data (plain markdown, last 20 sessions)
└── chronicle-manager.py            ← The CLI (Python 3.8+, stdlib only)

Per-tool adapters (installed to tool-specific locations):
├── Claude Code  → ~/.claude/hooks/ + ~/.claude/rules/
├── Codex CLI    → ~/.codex/AGENTS.md
├── Gemini CLI   → ~/.gemini/GEMINI.md
└── Cursor       → ~/.cursor/rules/
```

**Key design decisions:**
- **No external services** — just files and a Python script
- **No per-prompt injection** — briefing injected once at session start, never mid-conversation
- **No pip dependencies** — Python stdlib only, runs everywhere
- **Tool-agnostic data** — plain markdown, any tool can read/write it
- **Fixed token budget** — ~300 tokens at session start, doesn't grow

## Entry Writing Protocol (for all tools)

**When to write:**
- After completing a significant task or milestone
- Before clearing context / starting fresh
- When the user signals they're done

**What to write:**
- 3-5 bullets: what changed, key decisions, current status, next steps
- Specific enough to resume cold without re-explaining
- From the user's perspective, not implementation minutiae

**What NOT to do:**
- Don't update for trivial interactions
- Don't assume the user wants to continue their last task
- Don't write a novel — 50-80 tokens per entry

## License

MIT
