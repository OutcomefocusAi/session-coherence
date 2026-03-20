# Session Coherence

**Cross-tool session memory for AI coding assistants. One chronicle, every tool.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776AB.svg)](https://python.org)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-green.svg)](#)
[![Tools Supported](https://img.shields.io/badge/Tools_Supported-9-orange.svg)](#supported-tools)

## Why

Every AI coding session starts cold. You re-explain which repo, what you were doing, what decisions you made. Switch from Claude Code to Cursor mid-project and the new tool knows nothing. Clear your context window and everything is gone.

Session Coherence fixes this. It maintains a rolling chronicle of your work sessions — a single markdown file that every AI tool reads at startup. Your decisions, blockers, and project status follow you across tools, context resets, and machines.

## How It's Different

|  | Session Coherence | claude-mem | Mem0 | Engram | Basic Memory |
|--|-------------------|-----------|------|--------|-------------|
| **Cross-tool** | 9 tools | Claude Code only | API clients | MCP only | MCP only |
| **Dependencies** | None (Python stdlib) | Bun + uv + Chroma | Cloud API / self-host | Go binary + SQLite | Node.js |
| **Token cost** | ~300 fixed, once | Variable per prompt | Variable per prompt | Variable per prompt | Variable per prompt |
| **Data format** | Plain markdown | SQLite | Graph DB | SQLite | Markdown |
| **Runs offline** | Always | Yes | No (cloud) / Yes (self-host) | Yes | Yes |
| **Setup time** | < 60 seconds | ~5 min | ~10 min | ~5 min | ~5 min |
| **Semantic tags** | Built-in | No | No | No | No |
| **File locking** | Yes | N/A | N/A | N/A | N/A |

**When to use something else:** If you need vector search at scale, graph-based entity relationships, or AI-compressed summaries, look at Mem0 or claude-mem. Session Coherence is for developers who want cross-tool session continuity with zero infrastructure.

## Quick Start

> **One install covers all your tools.** You clone the repo once, run one command, and every tool you use — Claude Code, Cursor, Gemini CLI, Codex, Aider, etc. — shares the same session history. No per-tool downloads, no separate configurations. Add a session summary in Claude Code, switch to Cursor, and Cursor sees it immediately.

### Install from source

```bash
git clone https://github.com/OutcomeFocusAi/session-coherence.git
cd session-coherence
bash install.sh all                  # All 9 tools at once
```

Or pick specific tools:

```bash
bash install.sh claude-code cursor gemini   # Just the ones you use
```

You can always add more tools later by re-running the installer — it won't duplicate anything.

### Install with pip

```bash
pip install session-coherence
session-coherence init
```

### Verify

```bash
python ~/.session-coherence/chronicle-manager.py status
python ~/.session-coherence/chronicle-manager.py briefing
```

That's it. Your next session starts with context.

## Supported Tools

| Tool | Integration | Auto-inject | Auto-capture | Adapter Type |
|------|------------|-------------|--------------|-------------|
| **Claude Code** | SessionStart hook | Yes | Via rule | Hook + Rule |
| **Codex CLI** | `~/.codex/AGENTS.md` | Yes | Via instructions | Instruction file |
| **Gemini CLI** | `~/.gemini/GEMINI.md` | Yes | Via instructions | Instruction file |
| **Cursor** | `~/.cursor/rules/` | Yes | Via rules | Rule file |
| **Aider** | `conventions.md` | Yes | Via conventions | Convention file |
| **Windsurf** | `.windsurfrules` | Yes | Via rules | Rule file |
| **Cline** | `.clinerules` | Yes | Via rules | Rule file |
| **GitHub Copilot** | `copilot-instructions` | Yes | Via instructions | Instruction file |
| **Zed** | Assistant rules | Yes | Via rules | Rule file |

Each adapter teaches the AI tool two things: (1) read the chronicle at session start, and (2) write a summary at natural breakpoints. The data format is identical across all tools.

## How It Works

```
                         ~/.session-coherence/
                        ┌─────────────────────┐
                        │   chronicle.md       │  Plain markdown
                        │   (last 20 sessions) │  Human-readable
                        └──────────┬───────────┘  Git-trackable
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
               ┌────▼────┐  ┌─────▼─────┐  ┌────▼────┐
               │  Parse   │  │   Write   │  │ Archive │
               │  & Tag   │  │  (add)    │  │ (rotate)│
               └────┬────┘  └───────────┘  └─────────┘
                    │
            ┌───────▼───────┐
            │  Structured   │   Extracts: active threads,
            │  Briefing     │   blockers, decisions, focus
            │  (~300 tokens)│
            └───────┬───────┘
                    │
     ┌──────────────┼──────────────────────┐
     │              │              │        │
  ┌──▼───┐    ┌────▼────┐   ┌────▼───┐  ┌─▼──────┐
  │Claude│    │ Codex   │   │ Gemini │  │ Cursor │  ...
  │Code  │    │ CLI     │   │ CLI    │  │        │
  │(hook)│    │(AGENTS) │   │(GEMINI)│  │(rules) │
  └──────┘    └─────────┘   └────────┘  └────────┘
```

**Session start:** The tool's adapter reads `chronicle.md`, parses semantic tags, and produces a structured briefing. For Claude Code, this happens via a SessionStart hook. For other tools, the adapter instructions tell the AI to read the file directly.

**During the session:** Zero cost. No per-prompt injection, no background processes, no API calls.

**Session end:** At natural breakpoints (task complete, before `/clear`, user says "done"), the AI writes 3-5 tagged bullets summarizing the session. The oldest entry is auto-trimmed when the chronicle exceeds 20 entries.

## CLI Reference

```bash
# Generate a session briefing (auto-detects format)
session-coherence briefing
session-coherence briefing --format structured       # Force structured
session-coherence briefing --format chronological    # Force chronological

# Add a session entry (auto-rotates at 20 entries)
session-coherence add \
  --project "my-app" \
  --title "Added auth flow" \
  --bullets "- Implemented JWT auth in api/auth.ts" \
           "- [decision] JWT over sessions for stateless API" \
           "- [status] Auth complete, need password reset" \
           "- [next] Implement password reset flow"

# Search across all history (active + archived)
session-coherence search "JWT auth"

# Update an existing entry's bullets
session-coherence update --project "my-app" --bullets "- [status] Auth + password reset complete"

# Manually rotate (usually not needed — add auto-rotates)
session-coherence rotate --max-entries 20

# Export chronicle to JSON
session-coherence export --format json

# Show session analytics
session-coherence analytics

# Validate chronicle structure
session-coherence validate

# Show status
session-coherence status

# Initialize a fresh chronicle
session-coherence init

# Configuration
session-coherence config --set briefing_format structured
session-coherence config --set max_entries 30
```

Or use the manager script directly:

```bash
python ~/.session-coherence/chronicle-manager.py briefing
python ~/.session-coherence/chronicle-manager.py add --project "my-app" --title "Fixed auth" --bullets "- Fixed JWT expiry"
python ~/.session-coherence/chronicle-manager.py status
```

## Semantic Tags

Tags turn plain bullets into structured intelligence. The briefing engine extracts tagged bullets into dedicated sections (Active Threads, Blockers, Decisions, Focus) instead of showing a flat timeline.

| Tag | Purpose | Example |
|-----|---------|---------|
| `[change]` | What was modified (default if no tag) | `- Fixed retry logic in webhook handler` |
| `[decision]` | Choices made, with reasoning | `- [decision] JWT over sessions — stateless API` |
| `[blocker]` | What's stuck and why | `- [blocker] LinkedIn API approval pending` |
| `[status]` | Current state of the project | `- [status] M2 complete, M3 planning next` |
| `[next]` | Immediate follow-up | `- [next] Implement password reset flow` |
| `[priority]` | Top focus item | `- [priority] Ship v2.0 before Friday` |

Tags are optional. Untagged bullets default to `[change]`. Fully backward compatible with plain entries.

### Example Entry

```markdown
### 2026-03-16 16:45 | outcome-focus | M2 webhook fix
- Fixed Stripe webhook retry in api/webhooks/stripe.ts
- Updated error handling to surface failures to dashboard
- All M2 tests passing (147/147)
- [decision] Exponential backoff for M3 retry strategy
- [status] M2 complete, M3 planning next
```

### Example Briefing (generated from tagged entries)

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

When no tagged bullets exist, the briefing automatically falls back to a chronological format.

## Configuration

Create `~/.session-coherence/config.json` to customize behavior:

```json
{
  "briefing_format": "auto",
  "max_entries": 20,
  "archive_enabled": true
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `briefing_format` | `"auto"` | `"auto"`, `"structured"`, or `"chronological"` |
| `max_entries` | `20` | Max entries before rotation |
| `archive_enabled` | `true` | Archive rotated entries instead of deleting |

## Plugin System

Extend the briefing with custom hooks. Place `.py` files in `~/.session-coherence/plugins/` — they run in alphabetical order at session start.

Each plugin receives the briefing text and returns modified text:

```python
# ~/.session-coherence/plugins/greeting.py

def hook(briefing_text: str) -> str:
    return briefing_text + "\n\nReminder: check open PRs before starting."
```

Plugins can integrate with external systems (Qdrant, vector search, APIs) without touching the core code. If a plugin fails, it is skipped silently — plugins never block session start.

## Architecture

```
~/.session-coherence/                  Shared by all tools
├── chronicle.md                       The data (plain markdown, last 20 sessions)
├── chronicle-manager.py               The CLI (Python 3.8+, stdlib only)
├── config.json                        Optional configuration
├── archive/                           Rotated entries (searchable)
└── plugins/                           Briefing hook extensions

Per-tool adapters (installed to tool-specific locations):
├── Claude Code  → ~/.claude/hooks/session-briefing.py
│                  ~/.claude/rules/session-coherence.md
│                  ~/.claude/settings.json (auto-patched)
├── Codex CLI    → ~/.codex/AGENTS.md
├── Gemini CLI   → ~/.gemini/GEMINI.md
├── Cursor       → ~/.cursor/rules/session-coherence.md
├── Aider        → conventions.md
├── Windsurf     → .windsurfrules
├── Cline        → .clinerules
├── Copilot      → copilot-instructions
└── Zed          → assistant rules
```

**Design principles:**

- **No external services.** Just files and a Python script. No Docker, no databases, no API keys.
- **No per-prompt cost.** Briefing injected once at session start (~300 tokens). Zero tokens mid-session.
- **No pip dependencies.** Python stdlib only. Works on any machine with Python 3.8+.
- **Tool-agnostic data.** Plain markdown. Any tool, any editor, any script can read and write it.
- **Safe concurrency.** File locking prevents corruption when multiple tools write simultaneously.
- **Non-assumptive.** The briefing shows context but never assumes you want to continue. Your AI waits for direction.

## vs Other Tools

### claude-mem (38k+ stars)
AI-compressed session memory with sophisticated summarization. Great if you only use Claude Code and want automatic compression. Session Coherence is for developers who use multiple tools and want zero-dependency, fixed-cost session context.

### Mem0 (50k+ stars)
Production-grade graph memory with entity extraction and relationships. The right choice for teams building memory-augmented applications at scale. Session Coherence is for individual developers who want local-first session continuity without cloud infrastructure.

### Engram (1.6k stars)
Similar minimalist philosophy (Go binary, SQLite). Works through MCP only. Session Coherence provides native adapters for 9 tools and uses plain markdown instead of a database.

### Basic Memory (2.7k stars)
Markdown-first approach (aligned with our philosophy) but MCP-only integration without semantic tags or structured briefings. Session Coherence adds cross-tool adapters and tagged bullets for intelligent briefing generation.

### Supermemory (17k stars)
Cloud-based memory service with browser extension. Privacy-conscious developers may prefer Session Coherence's fully local, no-telemetry approach.

### claude-diary (343 stars)
Manual diary entries without auto-injection or cross-tool support. Session Coherence automates the injection and works across 9 tools.

### Pieces
Commercial OS-level context capture with impressive scope. Requires a desktop app and is not open-source. Session Coherence is MIT-licensed, runs anywhere Python does, and stores data in a format you control.

## FAQ

**Why not just use CLAUDE.md / AGENTS.md?**
Those files are static instructions — they tell the AI *how* to behave. The chronicle is temporal session history — it tells the AI *what you've been working on*. They're complementary.

**Why markdown and not SQLite?**
Markdown is human-readable in any editor, git-trackable for version history, and grep-able without special tooling. You can open `chronicle.md` in Notepad and understand your session history. SQLite requires dedicated tools to inspect.

**Will this slow down my session start?**
The briefing hook has a 3-second timeout. If it hangs for any reason, it is skipped and your session starts normally. The ~300 token injection is smaller than most system prompts.

**Can two tools write at the same time?**
Yes. File locking prevents corruption from concurrent writes. You can have Claude Code and Cursor writing to the same chronicle without conflicts.

**Does it phone home?**
No. Zero network calls, zero telemetry, zero cloud dependencies. Everything stays on your machine.

**What happens to old entries?**
When the chronicle exceeds 20 entries (configurable), the oldest are rotated to an archive. You can search the archive with `session-coherence search`.

## Uninstall

```bash
bash uninstall.sh all                  # Remove everything
bash uninstall.sh claude-code          # Remove specific tool
bash uninstall.sh all --keep-data      # Remove adapters, keep chronicle
bash uninstall.sh all --force          # Skip confirmation prompts
```

The uninstaller cleanly removes adapter files and auto-patches `settings.json` to remove hook entries.

## Pair With Claude Learn

Session Coherence tells your AI **what you've been working on**. [Claude Learn](https://github.com/OutcomeFocusAi/claude-learn) teaches your AI **how to work better** — self-improving behavioral rules with scored feedback loops and collective intelligence. Together, they give every session memory AND learning. Zero infrastructure for both.

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test with at least one tool adapter
5. Submit a pull request

Bug reports and feature requests: [GitHub Issues](https://github.com/OutcomeFocusAi/session-coherence/issues)

## License

[MIT](LICENSE)
