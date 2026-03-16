# Session Coherence Protocol

## Cross-Session Awareness

At the **start of each session**, read the session chronicle for context on recent work:

```
~/.session-coherence/chronicle.md
```

This file contains a rolling log of the last 20 sessions across all AI tools. Use it for awareness — do NOT assume the user wants to continue their last task. Wait for direction.

## Writing Session Entries

At natural breakpoints (task completed, user says "done"), update the chronicle.
New entries go at the TOP of `~/.session-coherence/chronicle.md`:

```
### YYYY-MM-DD HH:MM | project-name | short title
- What changed (specific, not vague)
- Key decisions and reasoning
- Current status
- Open threads or next steps
```

Or use the CLI:
```bash
python ~/.session-coherence/chronicle-manager.py add --project "name" --title "title" --bullets "- item1" "- item2"
```

**Rules:** 3-5 bullets per entry. Capture decisions and blockers. Don't update for trivial interactions. The chronicle is awareness, not instructions.
