# Session Coherence

Cross-session awareness for AI coding tools. Each new session knows what you were working on — without context bloat.

## The Problem

Every new AI coding session starts cold. You re-explain which repo, what you were doing, what decisions were made. Context windows grow if you try to load everything. Memories go in but nothing comes back out.

## The Solution

A lightweight, rolling session chronicle shared across all your AI tools:

- **Fixed cost**: ~300 tokens injected once at session start, never grows
- **Rolling window**: Last 20 sessions, oldest auto-trimmed
- **Cross-tool**: Works with Claude Code, Codex CLI, Gemini CLI, Cursor
- **Not assumptive**: Presents recent work as context, doesn't assume continuation

## How It Works

```
Session Start                    During Session                Session End
┌─────────────┐                 ┌──────────────┐             ┌─────────────┐
│ Read         │                 │ No auto-     │             │ Write 3-5   │
│ chronicle    │──> ~300 token   │ injection    │             │ bullet      │──> chronicle
│ (last 20     │    briefing     │ Zero context │             │ summary     │    updated
│  sessions)   │    (one-time)   │ cost         │             │             │
└─────────────┘                 └──────────────┘             └─────────────┘
```

### Example Briefing

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

### Example Chronicle Entry

```markdown
### 2026-03-16 16:45 | outcome-focus | M2 webhook fix
- Fixed Stripe webhook retry in api/webhooks/stripe.ts (silent failure after 3rd retry)
- Updated error handling to surface failures to dashboard
- All M2 tests passing (147/147)
- Decision: exponential backoff for M3 retry strategy
- Status: M2 complete, M3 planning next
```

## Install

```bash
git clone https://github.com/OutcomefocusAi/session-coherence.git
cd session-coherence

# Install for specific tools
./install.sh claude-code
./install.sh codex gemini
./install.sh all
```

### Tool-Specific Setup

| Tool | Adapter | How It Works |
|------|---------|-------------|
| **Claude Code** | SessionStart hook | Auto-injects briefing on every session start |
| **Codex CLI** | AGENTS.md | Instructions tell Codex to read chronicle |
| **Gemini CLI** | GEMINI.md | Instructions tell Gemini to read chronicle |
| **Cursor** | .cursorrules | Rules snippet tells Cursor to read chronicle |

## CLI Reference

```bash
# Show current status
python ~/.session-coherence/chronicle-manager.py status

# Generate briefing (what the hook shows)
python ~/.session-coherence/chronicle-manager.py briefing

# Add a session entry
python ~/.session-coherence/chronicle-manager.py add \
  --project "my-app" \
  --title "Added auth flow" \
  --bullets "- Implemented JWT auth in api/auth.ts" \
           "- Added login/signup pages" \
           "- Tests passing (23/23)"

# Rotate old entries (auto-runs on add)
python ~/.session-coherence/chronicle-manager.py rotate --max-entries 20

# Initialize (first time)
python ~/.session-coherence/chronicle-manager.py init
```

## Architecture

```
~/.session-coherence/
├── chronicle.md            # The data — plain markdown, shared by all tools
└── chronicle-manager.py    # The CLI — parse, format, add, rotate

Adapters (per tool):
├── claude-code/            # Hook + rule (auto-injects at session start)
├── codex/                  # AGENTS.md (instruction-based)
├── gemini/                 # GEMINI.md (instruction-based)
└── cursor/                 # .cursorrules snippet (instruction-based)
```

**Key design decisions:**
- **No external services** — just files and a Python script (stdlib only)
- **No per-prompt injection** — briefing injected once, not on every message
- **Tool-agnostic data format** — plain markdown, any tool can read/write it
- **Fixed token budget** — ~300 tokens at session start, never grows mid-session

## Requirements

- Python 3.8+
- No pip dependencies (stdlib only)

## License

MIT
