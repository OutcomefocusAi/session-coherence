#!/usr/bin/env python3
"""Session Chronicle Manager — cross-tool session coherence.

A shared CLI for managing a rolling log of AI coding sessions.
Works with any AI tool (Claude Code, Codex CLI, Gemini CLI, Cursor, etc.)

Usage:
    chronicle-manager.py briefing [--format auto|structured|chronological]
    chronicle-manager.py add --project NAME --title TITLE [--bullets "- item1" "- item2" ...]
    chronicle-manager.py rotate [--max-entries N]
    chronicle-manager.py status
    chronicle-manager.py init

Environment:
    SESSION_CHRONICLE_PATH  Override default chronicle location
                            Default: ~/.session-coherence/chronicle.md
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# Tag parsing for structured bullets
TAG_RE = re.compile(r"^-\s+\[(\w+)\]\s+(.+)$")
VALID_TAGS = {"change", "decision", "blocker", "status", "next", "priority"}


def get_chronicle_path():
    """Get chronicle file path from env or default."""
    env_path = os.environ.get("SESSION_CHRONICLE_PATH")
    if env_path:
        return Path(env_path)
    return Path.home() / ".session-coherence" / "chronicle.md"


CHRONICLE_HEADER = "<!-- Session Chronicle — rolling log, last 20 sessions. Oldest entries auto-trimmed. -->"


def parse_bullet(line):
    """Parse a bullet line into a dict with tag, text, and raw fields.

    Tagged format: '- [decision] Chose JWT over sessions'
    Untagged format: '- Fixed the login bug' (defaults to tag='change')
    """
    m = TAG_RE.match(line)
    if m:
        tag = m.group(1).lower()
        if tag not in VALID_TAGS:
            tag = "change"
        return {"tag": tag, "text": m.group(2).strip(), "raw": line}
    # Untagged bullet — strip the leading "- "
    return {"tag": "change", "text": line[2:].strip(), "raw": line}


def parse_chronicle(text):
    """Parse chronicle into list of entry dicts (file order, newest first)."""
    entries = []
    current = None

    for line in text.splitlines():
        if line.startswith("### "):
            if current:
                entries.append(current)
            header = line[4:].strip()
            parts = [p.strip() for p in header.split("|")]
            current = {
                "header": header,
                "date": parts[0] if len(parts) > 0 else "",
                "project": parts[1] if len(parts) > 1 else "",
                "title": parts[2] if len(parts) > 2 else "",
                "bullets": [],
                "raw_lines": [line],
            }
        elif current:
            current["raw_lines"].append(line)
            if line.startswith("- "):
                current["bullets"].append(parse_bullet(line))

    if current:
        entries.append(current)

    return entries


def get_active_projects(entries, count=10):
    """Derive active projects from recent entries."""
    projects = {}
    for entry in entries[:count]:
        proj = entry["project"]
        if proj and proj not in projects:
            status = ""
            for b in entry["bullets"]:
                # Check for [status] tag or legacy "Status:" prefix
                if b["tag"] == "status":
                    status = b["text"]
                    break
                if b["text"].lower().startswith("status:"):
                    status = b["text"][len("status:"):].strip()
                    break
            projects[proj] = status or entry["title"]
    return projects


def extract_sections(entries, max_entries=10):
    """Extract semantic sections from recent chronicle entries.

    Returns a dict with:
        active_threads: dict of project -> most recent status/next (max 6)
        blockers: list of (text, project) tuples (max 4)
        decisions: list of decision texts (max 4)
        recent_work: list of (date, project, title) tuples (max 3)
        focus: most recent priority or next bullet, or None
    """
    active_threads = {}
    blockers = []
    decisions = []
    focus = None

    for entry in entries[:max_entries]:
        proj = entry["project"]

        # Build active thread from status/next tags
        if proj and proj not in active_threads:
            for b in entry["bullets"]:
                if b["tag"] in ("status", "next"):
                    active_threads[proj] = b["text"]
                    break
            # Fallback to title if no status/next tag
            if proj not in active_threads:
                active_threads[proj] = entry["title"]

        for b in entry["bullets"]:
            if b["tag"] == "blocker" and len(blockers) < 4:
                blockers.append((b["text"], proj))
            elif b["tag"] == "decision" and len(decisions) < 4:
                decisions.append(b["text"])
            elif b["tag"] == "priority" and focus is None:
                focus = b["text"]
            elif b["tag"] == "next" and focus is None:
                focus = b["text"]

    # Trim active threads to 6
    if len(active_threads) > 6:
        active_threads = dict(list(active_threads.items())[:6])

    recent_work = []
    for entry in entries[:3]:
        short_date = entry["date"].split(" ")[0] if " " in entry["date"] else entry["date"]
        recent_work.append((short_date, entry["project"], entry["title"]))

    return {
        "active_threads": active_threads,
        "blockers": blockers,
        "decisions": decisions,
        "recent_work": recent_work,
        "focus": focus,
    }


def has_semantic_tags(entries, max_entries=10):
    """Check if any recent entry has non-default tags (triggers structured mode)."""
    for entry in entries[:max_entries]:
        for b in entry["bullets"]:
            if b["tag"] != "change":
                return True
    return False


def format_structured_briefing(entries):
    """Format entries as a semantic structured briefing."""
    sections = extract_sections(entries)
    lines = ["## Session Briefing", ""]

    # Active threads
    if sections["active_threads"]:
        lines.append("Active Threads:")
        for proj, status in sections["active_threads"].items():
            lines.append(f"- {proj}: {status}")
        lines.append("")

    # Blockers
    if sections["blockers"]:
        lines.append("Blockers:")
        for text, proj in sections["blockers"]:
            lines.append(f"- {text} ({proj})")
        lines.append("")

    # Decisions
    if sections["decisions"]:
        lines.append("Recent Decisions:")
        for text in sections["decisions"]:
            lines.append(f"- {text}")
        lines.append("")

    # Recent work
    if sections["recent_work"]:
        lines.append("Last 3 Sessions:")
        for date, proj, title in sections["recent_work"]:
            lines.append(f"- {date}: {title} ({proj})")
        lines.append("")

    # Focus
    if sections["focus"]:
        lines.append(f"Focus: {sections['focus']}")
        lines.append("")

    # Hard cap
    if len(lines) > 25:
        lines = lines[:25]

    return "\n".join(lines).rstrip()


def format_chronological_briefing(entries, args):
    """Format entries as the original chronological briefing."""
    lines = ["## Session Briefing", ""]

    # Detailed entries
    detailed = entries[:args.detail]
    if detailed:
        lines.append("Recent work:")
        for entry in detailed:
            lines.append(f"- {entry['date']} | {entry['project']} | {entry['title']}")
            for bullet in entry["bullets"][:args.max_bullets]:
                lines.append(f"  > {bullet['text']}")
        lines.append("")

    # One-liners
    oneliners = entries[args.detail:args.detail + args.oneliner]
    if oneliners:
        parts = []
        for entry in oneliners:
            short = entry["date"].split(" ")[0] if " " in entry["date"] else entry["date"]
            parts.append(f"{short} {entry['project']} ({entry['title']})")
        lines.append("Older: " + ", ".join(parts))
        lines.append("")

    # Active projects
    projects = get_active_projects(entries)
    if projects:
        proj_parts = [f"{name} ({status})" for name, status in projects.items()]
        lines.append("Active projects: " + ", ".join(proj_parts))
        lines.append("")

    # Hard cap
    if len(lines) > 30:
        lines = lines[:30]

    return "\n".join(lines).rstrip()


def cmd_briefing(args):
    """Generate a session briefing from the chronicle."""
    path = get_chronicle_path()
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return

    entries = parse_chronicle(text)
    if not entries:
        return

    fmt = getattr(args, "format", "auto")

    if fmt == "structured":
        output = format_structured_briefing(entries)
    elif fmt == "chronological":
        output = format_chronological_briefing(entries, args)
    else:
        # Auto-detect: use structured if any tagged bullets found
        if has_semantic_tags(entries):
            output = format_structured_briefing(entries)
        else:
            output = format_chronological_briefing(entries, args)

    if output:
        print(output)


def cmd_add(args):
    """Add a new entry to the chronicle."""
    path = get_chronicle_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"### {now} | {args.project} | {args.title}"

    entry_lines = [header]
    if args.bullets:
        for bullet in args.bullets:
            if not bullet.startswith("- "):
                bullet = f"- {bullet}"
            entry_lines.append(bullet)

    new_entry = "\n".join(entry_lines)

    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
        # Split: header comment + rest
        lines = text.split("\n", 1)
        file_header = lines[0] if lines[0].startswith("<!--") else ""
        rest = lines[1].strip() if len(lines) > 1 else ""
        if not file_header:
            rest = text
            file_header = CHRONICLE_HEADER

        content = f"{file_header}\n\n{new_entry}\n\n{rest}\n"
    else:
        content = f"{CHRONICLE_HEADER}\n\n{new_entry}\n"

    path.write_text(content, encoding="utf-8")

    # Auto-rotate
    do_rotate(path, args.max_entries)

    print(f"Added: {args.project} | {args.title}")


def do_rotate(path, max_entries=20):
    """Trim chronicle to max_entries."""
    text = path.read_text(encoding="utf-8")
    entries = parse_chronicle(text)

    if len(entries) <= max_entries:
        return

    # Keep only the newest max_entries
    kept = entries[:max_entries]
    removed_count = len(entries) - max_entries

    # Rebuild file
    lines = [CHRONICLE_HEADER, ""]
    for entry in kept:
        lines.extend(entry["raw_lines"])
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    if removed_count > 0:
        print(f"Rotated: removed {removed_count} oldest entries, kept {max_entries}")


def cmd_rotate(args):
    """Manually rotate the chronicle."""
    path = get_chronicle_path()
    if not path.exists():
        print("No chronicle file found.")
        return
    do_rotate(path, args.max_entries)
    # Show status after
    cmd_status(args)


def cmd_status(args):
    """Show chronicle status."""
    path = get_chronicle_path()
    print(f"Chronicle: {path}")

    if not path.exists():
        print("Status: not initialized")
        print(f"Run: chronicle-manager.py init")
        return

    text = path.read_text(encoding="utf-8")
    entries = parse_chronicle(text)
    size = path.stat().st_size

    print(f"Entries: {len(entries)}")
    print(f"File size: {size} bytes")

    if entries:
        print(f"Latest: {entries[0]['date']} | {entries[0]['project']} | {entries[0]['title']}")
        if len(entries) > 1:
            print(f"Oldest: {entries[-1]['date']} | {entries[-1]['project']} | {entries[-1]['title']}")

        projects = get_active_projects(entries)
        if projects:
            print(f"Active projects: {', '.join(projects.keys())}")


def cmd_init(args):
    """Initialize the chronicle file and directory."""
    path = get_chronicle_path()

    if path.exists():
        print(f"Chronicle already exists at {path}")
        cmd_status(args)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{CHRONICLE_HEADER}\n", encoding="utf-8")
    print(f"Initialized: {path}")


def main():
    # Fix Unicode output on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Session Chronicle Manager — cross-tool session coherence"
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # briefing
    p_brief = sub.add_parser("briefing", help="Generate session briefing")
    p_brief.add_argument("--format", choices=["auto", "structured", "chronological"],
                         default="auto", help="Briefing format (default: auto)")
    p_brief.add_argument("--detail", type=int, default=5, help="Detailed entries count (default: 5)")
    p_brief.add_argument("--oneliner", type=int, default=10, help="One-liner entries count (default: 10)")
    p_brief.add_argument("--max-bullets", type=int, default=3, help="Max bullets per entry (default: 3)")

    # add
    p_add = sub.add_parser("add", help="Add a session entry")
    p_add.add_argument("--project", required=True, help="Project name")
    p_add.add_argument("--title", required=True, help="Short session title")
    p_add.add_argument("--bullets", nargs="*", help="Bullet points (use quotes)")
    p_add.add_argument("--max-entries", type=int, default=20, help="Max entries to keep (default: 20)")

    # rotate
    p_rot = sub.add_parser("rotate", help="Trim old entries")
    p_rot.add_argument("--max-entries", type=int, default=20, help="Max entries to keep (default: 20)")

    # status
    sub.add_parser("status", help="Show chronicle status")

    # init
    sub.add_parser("init", help="Initialize chronicle file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "briefing": cmd_briefing,
        "add": cmd_add,
        "rotate": cmd_rotate,
        "status": cmd_status,
        "init": cmd_init,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
