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
  --bullets "- What changed (specific files, features, decisions)" \
           "- Key decisions and reasoning" \
           "- Current status (tests passing/failing, blocked, ready for X)" \
           "- Open threads or next steps"
```

Or edit `~/.session-coherence/chronicle.md` directly. New entries go at the TOP (after the HTML comment header):

```
### YYYY-MM-DD HH:MM | project-name | short descriptive title
- What changed (specific files, features, or decisions — not vague)
- Key decisions made and reasoning
- Current status (tests passing/failing, blocked on X, ready for Y)
- Open threads or next steps if any
- [optional 5th bullet only if warranted]
```

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
