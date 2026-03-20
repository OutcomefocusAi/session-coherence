# Session Coherence Protocol

## The Session Chronicle

**File:** `~/.session-coherence/chronicle.md`
**Manager:** `~/.session-coherence/chronicle-manager.py`

Rolling log of the last 20 sessions across all AI tools. Read automatically at session start by a hook — Claude does NOT need to re-read it. Claude DOES need to write to it at natural breakpoints.

---

## When to Update

Update the session chronicle at these moments:

1. **After completing a significant task or milestone** — the main trigger
2. **Before running `/clear`** — capture what happened before context is wiped
3. **When the user signals they're done** — "that's it", "we're good", "done for now", "signing off"
4. **Before a long debugging/research pivot** — capture the stable state before diving in

**Do NOT update for:**
- Trivial interactions (quick questions, single lookups, "what time is it")
- Mid-task (wait until something meaningful is complete)
- If the session is just starting and nothing has happened yet

---

## How to Write an Entry

Use the chronicle manager CLI:

```bash
python ~/.session-coherence/chronicle-manager.py add \
  --project "project-name" \
  --title "short descriptive title" \
  --bullets "- [decision] Chose X over Y because Z" \
           "- [status] Feature complete, tests passing" \
           "- [next] Need to implement error handling" \
           "- Implemented auth flow in api/auth.ts"
```

Or edit `~/.session-coherence/chronicle.md` directly. New entries go at the TOP (after the HTML comment header):

```
### YYYY-MM-DD HH:MM | project-name | short descriptive title
- [decision] Key choice made and reasoning
- [status] Current state (tests passing/failing, deployed, blocked)
- [blocker] What's stuck and why
- [next] Immediate next step or follow-up
- [priority] Most important thing to focus on
- Plain bullet without tag (treated as a change)
```

### Tag Reference

| Tag | Purpose | Example |
|-----|---------|---------|
| `[change]` | What was modified (default if no tag) | `- [change] Rewrote auth middleware` |
| `[decision]` | Choices made with reasoning | `- [decision] JWT over sessions — stateless API` |
| `[blocker]` | What's stuck | `- [blocker] LinkedIn API approval pending` |
| `[status]` | Current state | `- [status] M2 complete, M3 planning next` |
| `[next]` | Immediate follow-up | `- [next] Implement password reset flow` |
| `[priority]` | Top focus item | `- [priority] Ship v2.0 before Friday` |

Tags are **optional** — untagged bullets default to `[change]`. Backward compatible with existing entries.

**project-name**: derive from the repo/directory being worked on. Use `home` for general system work.

---

## Rotation

The chronicle-manager handles rotation automatically when adding entries. Manual rotation:

```bash
python ~/.session-coherence/chronicle-manager.py rotate --max-entries 20
```

---

## Quality Guidelines

- Write from the **user's perspective** of what matters, not implementation minutiae
- Include enough detail to resume cold: "Fixed X in Y file because Z" not just "Fixed a bug"
- Capture **decisions** — these are the highest-value memories
- Note **blockers** explicitly — future sessions need to know what's stuck
- Use tags for decisions, blockers, status, and next steps — they power the structured briefing
- Keep each entry to 3-5 bullets, ~50-80 tokens

---

## Non-Assumptive Behavior

The session chronicle provides **context about recent work**. It is background awareness.

- Do NOT assume the user wants to continue their last task
- Do NOT automatically cd into the last project
- Do NOT start executing where the last session left off
- DO reference the chronicle naturally when the user asks about recent work
- DO use it to avoid asking questions the chronicle already answers

Wait for the user's direction. The briefing is a menu of recent context, not a set of instructions.
