#!/usr/bin/env python3
"""Claude Code SessionStart hook — injects cross-session briefing into context.

Calls chronicle-manager.py for the briefing, then optionally appends
Qdrant guard memories if available locally.

Install: Copy to ~/.claude/hooks/ and add to settings.json SessionStart hooks.
Must always exit 0 — never block session start.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Skip for Paperclip agent runs (agents get their own context)
if os.environ.get('PAPERCLIP_AGENT_ID'):
    sys.exit(0)


# chronicle-manager.py location — set by installer or default to repo location
MANAGER_SCRIPT = Path.home() / ".session-coherence" / "chronicle-manager.py"
QDRANT_URL = "http://localhost:6333"


def get_briefing():
    """Get briefing from chronicle-manager."""
    if not MANAGER_SCRIPT.exists():
        return ""

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            ["python", str(MANAGER_SCRIPT), "briefing"],
            capture_output=True, text=True, timeout=3, env=env
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def get_qdrant_guards():
    """Pull guard memories from local Qdrant if available."""
    try:
        import requests
        resp = requests.get(f"{QDRANT_URL}/", timeout=1)
        if resp.status_code != 200:
            return []
    except Exception:
        return []

    try:
        script = Path.home() / ".claude" / "scripts" / "qdrant-memory.py"
        if not script.exists():
            return []

        result = subprocess.run(
            ["python", str(script), "search-memory",
             "guard never always must not prefer not", "--limit", "5"],
            capture_output=True, text=True, timeout=4
        )
        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)
        guards = []
        for item in data:
            payload = item.get("payload", item)
            guard_type = payload.get("guard_type", "")
            if guard_type in ("hard", "soft"):
                text = payload.get("text", "")
                if text:
                    if len(text) > 80:
                        text = text[:77] + "..."
                    guards.append(text)
        return guards[:3]
    except Exception:
        return []


def main():
    try:
        briefing = get_briefing()
        if not briefing:
            sys.exit(0)

        print(briefing)

        # Append guards if Qdrant is available (Claude Code specific)
        guards = get_qdrant_guards()
        if guards:
            print(f"\nGuards: {' | '.join(guards)}")

    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
