# Session Coherence Protocol

## Cross-Session Awareness

At the **start of each session**, read the session chronicle for context on recent work:

```
~/.session-coherence/chronicle.md
```

This file contains a rolling log of the last 20 sessions across all AI tools. Use it for awareness — do NOT assume the user wants to continue their last task. Wait for direction.

## Writing Session Entries

At natural breakpoints (task completed, user says "done", before context reset), add an entry using the chronicle manager:

```bash
python ~/.session-coherence/chronicle-manager.py add \
  --project "project-name" \
  --title "short descriptive title" \
  --bullets "- [decision] Key choice" "- [status] Current state" "- What changed" "- [next] Follow-up"
```

Or edit `~/.session-coherence/chronicle.md` directly. New entries go at the TOP:

```
### YYYY-MM-DD HH:MM | project-name | short title
- [decision] Key choice and reasoning
- [status] Current state
- What changed (specific, not vague)
- [next] Open threads or next steps
```

**Optional tags:** `[change]` (default), `[decision]`, `[blocker]`, `[status]`, `[next]`, `[priority]`. Untagged bullets = change.

**Rules:**
- 3-5 bullets per entry, ~50-80 tokens
- Write from the user's perspective, not implementation minutiae
- Capture decisions (highest-value memories) and blockers
- Don't update for trivial interactions
- Don't assume continuation — the chronicle is a menu, not instructions
