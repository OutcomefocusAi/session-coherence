# Session Coherence

Cross-session awareness for AI coding tools. Each new session knows what you were working on — without context bloat.

Works with **Claude Code**, **Codex CLI**, **Gemini CLI**, and **Cursor**.

## The Problem

Every new AI coding session starts cold. You re-explain which repo, what you were doing, what decisions were made. Context windows grow if you try to load everything.

## The Solution

A rolling session chronicle — a single markdown file shared across all your AI tools:

- **Fixed cost**: ~500-800 tokens at session start, never grows mid-session
- **Rolling window**: Last 20 sessions, oldest auto-trimmed
- **Cross-tool**: All tools read/write the same file
- **Not assumptive**: Shows recent work as context, doesn't assume continuation
- **Structured**: Tagged bullets power semantic briefings with active threads, blockers, and decisions

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
│ chronicle    │──> ~500-800     │ injection    │             │ tagged      │──> chronicle
│ (last 20     │    token        │ Zero cost    │             │ bullet      │    updated
│  sessions)   │    briefing     │ mid-session  │             │ summary     │
└─────────────┘                 └──────────────┘             └─────────────┘
```

### Example Briefing (structured format — what you see at session start)

```
## Session Briefing

Active Threads:
- claude-learn: v3.1.0 shipped, collective intelligence live
- outcome-focus: M2 complete, M3 planning next
- claude-voice: PTT blocked, needs async keep-alive

Blockers:
- LinkedIn API approval pending — all post analytics blocked (outcome-focus)

Recent Decisions:
- JWT over sessions for auth — stateless API
- Exponential backoff for M3 retry strategy

Last 3 Sessions:
- Mar 20: Built and shipped claude-learn plugin v3.1.0 (claude-learn)
- Mar 19: Built two marketing demo videos (remotion-studio)
- Mar 18: Social media analytics implementation (outcome-focus)

Focus: Ship v2.0 before Friday
```

When no tagged bullets exist, the briefing falls back to a chronological format automatically.

### Example Chronicle Entry (what gets written)

```markdown
### 2026-03-16 16:45 | outcome-focus | M2 webhook fix
- Fixed Stripe webhook retry in api/webhooks/stripe.ts (silent failure after 3rd retry)
- Updated error handling to surface failures to dashboard
- All M2 tests passing (147/147)
- [decision] Exponential backoff for M3 retry strategy
- [status] M2 complete, M3 planning next
```

### Bullet Tags

| Tag | Purpose |
|-----|---------|
| `[change]` | What was modified (default if no tag) |
| `[decision]` | Choices made with reasoning |
| `[blocker]` | What's stuck and why |
| `[status]` | Current state of the project |
| `[next]` | Immediate follow-up or next step |
| `[priority]` | Top focus item |

Tags are **optional** — untagged bullets default to `[change]`. Fully backward compatible with existing entries.

## CLI Reference

```bash
# Check status
python ~/.session-coherence/chronicle-manager.py status

# Generate briefing (auto-detects structured vs chronological)
python ~/.session-coherence/chronicle-manager.py briefing

# Force structured format
python ~/.session-coherence/chronicle-manager.py briefing --format structured

# Force chronological (legacy) format
python ~/.session-coherence/chronicle-manager.py briefing --format chronological

# Add a session entry with tags (auto-rotates if > 20 entries)
python ~/.session-coherence/chronicle-manager.py add \
  --project "my-app" \
  --title "Added auth flow" \
  --bullets "- Implemented JWT auth in api/auth.ts" \
           "- [decision] JWT over sessions for stateless API" \
           "- [status] Auth complete, need password reset next" \
           "- [next] Implement password reset flow"

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
- **Fixed token budget** — ~500-800 tokens at session start, doesn't grow
- **Semantic structure** — tagged bullets enable structured briefings without breaking backward compatibility

## Entry Writing Protocol (for all tools)

**When to write:**
- After completing a significant task or milestone
- Before clearing context / starting fresh
- When the user signals they're done

**What to write:**
- 3-5 bullets: what changed, key decisions, current status, next steps
- Use `[decision]`, `[blocker]`, `[status]`, `[next]` tags for high-signal bullets
- Specific enough to resume cold without re-explaining
- From the user's perspective, not implementation minutiae

**What NOT to do:**
- Don't update for trivial interactions
- Don't assume the user wants to continue their last task
- Don't write a novel — 50-80 tokens per entry

## License

MIT
