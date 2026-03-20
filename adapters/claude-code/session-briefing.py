#!/usr/bin/env python3
"""Claude Code SessionStart hook — injects cross-session briefing into context.

Calls chronicle-manager.py for the briefing, then runs any plugins found
in ~/.session-coherence/plugins/ to extend/modify the briefing.

Plugin system:
  - Place .py files in ~/.session-coherence/plugins/
  - Each plugin must define: hook(briefing_text: str) -> str
  - Plugins are loaded in alphabetical order
  - If a plugin fails, it is skipped with a warning (never blocks session start)

Example plugin (~/.session-coherence/plugins/greeting.py):

    def hook(briefing_text: str) -> str:
        return briefing_text + "\\n\\nGood morning! Remember to check PRs."

Install: Copy to ~/.claude/hooks/ and add to settings.json SessionStart hooks.
Must always exit 0 — never block session start.
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

# Skip for Paperclip agent runs (agents get their own context)
if os.environ.get('PAPERCLIP_AGENT_ID'):
    sys.exit(0)


# Cross-platform paths
COHERENCE_DIR = Path.home() / ".session-coherence"
MANAGER_SCRIPT = COHERENCE_DIR / "chronicle-manager.py"
PLUGINS_DIR = COHERENCE_DIR / "plugins"
CONFIG_FILE = COHERENCE_DIR / "config.json"


def detect_python():
    """Return the Python command available on this system."""
    # On Windows, 'py' is the launcher; on Unix, 'python3' is standard
    candidates = ["python3", "python", "py"] if os.name != "nt" else ["py", "python3", "python"]
    for cmd in candidates:
        try:
            result = subprocess.run(
                [cmd, "--version"], capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and "Python 3" in result.stdout + result.stderr:
                return cmd
        except Exception:
            continue
    return "python"


def get_config():
    """Load config.json if it exists."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_briefing():
    """Get briefing from chronicle-manager."""
    if not MANAGER_SCRIPT.exists():
        return ""

    try:
        python_cmd = detect_python()
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [python_cmd, str(MANAGER_SCRIPT), "briefing"]

        # Check config for briefing_format
        config = get_config()
        briefing_format = config.get("briefing_format")
        if briefing_format:
            cmd.extend(["--format", str(briefing_format)])

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3, env=env
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def run_plugins(briefing_text):
    """Load and run plugins from ~/.session-coherence/plugins/ in alphabetical order."""
    if not PLUGINS_DIR.is_dir():
        return briefing_text

    plugin_files = sorted(PLUGINS_DIR.glob("*.py"))
    if not plugin_files:
        return briefing_text

    for plugin_path in plugin_files:
        try:
            spec = importlib.util.spec_from_file_location(
                f"sc_plugin_{plugin_path.stem}", str(plugin_path)
            )
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "hook") and callable(module.hook):
                result = module.hook(briefing_text)
                if isinstance(result, str):
                    briefing_text = result
        except Exception as e:
            # Log warning but never block session start
            print(f"[session-coherence] plugin {plugin_path.name} failed: {e}",
                  file=sys.stderr)
            continue

    return briefing_text


def main():
    try:
        briefing = get_briefing()
        if not briefing:
            sys.exit(0)

        # Run plugins to extend/modify the briefing
        briefing = run_plugins(briefing)

        if briefing:
            print(briefing)

    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
