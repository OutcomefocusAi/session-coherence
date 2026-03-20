#!/usr/bin/env python3
"""Session Chronicle Manager v2.0 — cross-tool session coherence.

A shared CLI for managing a rolling log of AI coding sessions.
Works with any AI tool (Claude Code, Codex CLI, Gemini CLI, Cursor, etc.)

Usage:
    chronicle-manager.py briefing [--format auto|structured|chronological]
    chronicle-manager.py add --project NAME --title TITLE [--bullets "- item1" ...]
    chronicle-manager.py update --entry N [--add-bullet "- text"] [--set-title "title"]
    chronicle-manager.py rotate [--max-entries N]
    chronicle-manager.py search "query" [--project NAME] [--tag TAG] [--since DATE]
    chronicle-manager.py archive [--restore N]
    chronicle-manager.py export [--format json|csv|markdown] [--include-archive]
    chronicle-manager.py analytics
    chronicle-manager.py validate
    chronicle-manager.py config [--set KEY VALUE] [--reset]
    chronicle-manager.py status
    chronicle-manager.py init

Global flags:
    --json              JSON output for any command
    --quiet             Suppress non-essential output
    --verbose           Extra debug info
    --config PATH       Use alternate config file
    --chronicle PATH    Override chronicle path

Environment:
    SESSION_CHRONICLE_PATH  Override default chronicle location
                            Default: ~/.session-coherence/chronicle.md
"""

# =============================================================================
# 1. Imports and Constants
# =============================================================================

import argparse
import csv
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "2.0.0"

# Tag parsing for structured bullets
TAG_RE = re.compile(r"^-\s+\[(\w+)\]\s+(.+)$")
VALID_TAGS = {"change", "decision", "blocker", "status", "next", "priority"}

CHRONICLE_HEADER = "<!-- Session Chronicle — rolling log, last 20 sessions. Oldest entries auto-trimmed. -->"
ARCHIVE_HEADER = "<!-- Session Chronicle Archive — rotated entries preserved here. -->"

DEFAULT_CONFIG = {
    "max_entries": 20,
    "archive_enabled": True,
    "briefing_format": "auto",
    "briefing_max_lines": 25,
    "chronicle_path": "",
    "plugins_dir": "",
    "json_output": False,
}


# =============================================================================
# 2. Config Management
# =============================================================================

def get_config_path(override: Optional[str] = None) -> Path:
    """Get config file path."""
    if override:
        return Path(override)
    return Path.home() / ".session-coherence" / "config.json"


def load_config(override_path: Optional[str] = None) -> Dict[str, Any]:
    """Load config from file, falling back to defaults."""
    config = dict(DEFAULT_CONFIG)
    path = get_config_path(override_path)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            for k, v in user_config.items():
                if k in DEFAULT_CONFIG:
                    config[k] = v
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save_config(config: Dict[str, Any], override_path: Optional[str] = None) -> None:
    """Save config to file."""
    path = get_config_path(override_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_chronicle_path(args: Optional[argparse.Namespace] = None, config: Optional[Dict] = None) -> Path:
    """Get chronicle file path from args, env, config, or default."""
    # CLI flag takes highest priority
    if args and getattr(args, "chronicle", None):
        return Path(args.chronicle)
    # Env var next
    env_path = os.environ.get("SESSION_CHRONICLE_PATH")
    if env_path:
        return Path(env_path)
    # Config next
    if config and config.get("chronicle_path"):
        return Path(config["chronicle_path"])
    return Path.home() / ".session-coherence" / "chronicle.md"


def get_archive_path(chronicle_path: Path) -> Path:
    """Get archive file path (same directory as chronicle)."""
    return chronicle_path.parent / "archive.md"


# =============================================================================
# 3. File Locking
# =============================================================================

class FileLock:
    """Cross-platform file locking context manager.

    Uses fcntl on Unix and msvcrt on Windows. Falls back to no-op
    if neither is available.
    """

    def __init__(self, path: Path, timeout: float = 3.0):
        self.path = path
        self.timeout = timeout
        self._lock_path = path.parent / f".{path.name}.lock"
        self._fh = None

    def __enter__(self) -> "FileLock":
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self._lock_path, "w", encoding="utf-8")
        deadline = time.monotonic() + self.timeout
        attempts = 0
        while True:
            try:
                self._lock(self._fh)
                return self
            except (OSError, IOError):
                attempts += 1
                if time.monotonic() >= deadline:
                    if attempts > 1:
                        # Retry once more after a brief pause
                        try:
                            time.sleep(0.5)
                            self._lock(self._fh)
                            return self
                        except (OSError, IOError):
                            pass
                    raise TimeoutError(
                        f"Could not acquire lock on {self.path} after {self.timeout}s"
                    )
                time.sleep(0.1)

    def __exit__(self, *exc: Any) -> None:
        if self._fh:
            try:
                self._unlock(self._fh)
            except (OSError, IOError):
                pass
            self._fh.close()
            try:
                self._lock_path.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _lock(fh: Any) -> None:
        """Acquire exclusive lock."""
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(fh: Any) -> None:
        """Release lock."""
        if sys.platform == "win32":
            import msvcrt
            try:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            except (OSError, IOError):
                pass
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


# =============================================================================
# 4. Chronicle Parsing
# =============================================================================

def parse_bullet(line: str) -> Dict[str, str]:
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


def parse_chronicle(text: str) -> List[Dict[str, Any]]:
    """Parse chronicle into list of entry dicts (file order, newest first)."""
    entries: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

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


def rebuild_chronicle(entries: List[Dict[str, Any]], header: str = CHRONICLE_HEADER) -> str:
    """Rebuild chronicle text from parsed entries."""
    lines = [header, ""]
    for entry in entries:
        lines.extend(entry["raw_lines"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def entry_to_dict(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Convert parsed entry to a clean JSON-serializable dict."""
    tags = list({b["tag"] for b in entry["bullets"]})
    return {
        "date": entry["date"],
        "project": entry["project"],
        "title": entry["title"],
        "bullets": [{"tag": b["tag"], "text": b["text"]} for b in entry["bullets"]],
        "tags": tags,
    }


# =============================================================================
# 5. Briefing Generation
# =============================================================================

def get_active_projects(entries: List[Dict], count: int = 10) -> Dict[str, str]:
    """Derive active projects from recent entries."""
    projects: Dict[str, str] = {}
    for entry in entries[:count]:
        proj = entry["project"]
        if proj and proj not in projects:
            status = ""
            for b in entry["bullets"]:
                if b["tag"] == "status":
                    status = b["text"]
                    break
                if b["text"].lower().startswith("status:"):
                    status = b["text"][len("status:"):].strip()
                    break
            projects[proj] = status or entry["title"]
    return projects


def extract_sections(entries: List[Dict], max_entries: int = 10) -> Dict[str, Any]:
    """Extract semantic sections from recent chronicle entries.

    Returns a dict with:
        active_threads: dict of project -> most recent status/next (max 6)
        blockers: list of (text, project) tuples (max 4)
        decisions: list of decision texts (max 4)
        recent_work: list of (date, project, title) tuples (max 3)
        focus: most recent priority or next bullet, or None
    """
    active_threads: Dict[str, str] = {}
    blockers: List[Tuple[str, str]] = []
    decisions: List[str] = []
    focus: Optional[str] = None

    for entry in entries[:max_entries]:
        proj = entry["project"]

        if proj and proj not in active_threads:
            for b in entry["bullets"]:
                if b["tag"] in ("status", "next"):
                    active_threads[proj] = b["text"]
                    break
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


def has_semantic_tags(entries: List[Dict], max_entries: int = 10) -> bool:
    """Check if any recent entry has non-default tags (triggers structured mode)."""
    for entry in entries[:max_entries]:
        for b in entry["bullets"]:
            if b["tag"] != "change":
                return True
    return False


def format_structured_briefing(entries: List[Dict], max_lines: int = 25) -> str:
    """Format entries as a semantic structured briefing."""
    sections = extract_sections(entries)
    lines = ["## Session Briefing", ""]

    if sections["active_threads"]:
        lines.append("Active Threads:")
        for proj, status in sections["active_threads"].items():
            lines.append(f"- {proj}: {status}")
        lines.append("")

    if sections["blockers"]:
        lines.append("Blockers:")
        for text, proj in sections["blockers"]:
            lines.append(f"- {text} ({proj})")
        lines.append("")

    if sections["decisions"]:
        lines.append("Recent Decisions:")
        for text in sections["decisions"]:
            lines.append(f"- {text}")
        lines.append("")

    if sections["recent_work"]:
        lines.append("Last 3 Sessions:")
        for date, proj, title in sections["recent_work"]:
            lines.append(f"- {date}: {title} ({proj})")
        lines.append("")

    if sections["focus"]:
        lines.append(f"Focus: {sections['focus']}")
        lines.append("")

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    return "\n".join(lines).rstrip()


def format_chronological_briefing(entries: List[Dict], args: argparse.Namespace) -> str:
    """Format entries as the original chronological briefing."""
    lines = ["## Session Briefing", ""]

    detail = getattr(args, "detail", 5)
    oneliner = getattr(args, "oneliner", 10)
    max_bullets = getattr(args, "max_bullets", 3)

    detailed = entries[:detail]
    if detailed:
        lines.append("Recent work:")
        for entry in detailed:
            lines.append(f"- {entry['date']} | {entry['project']} | {entry['title']}")
            for bullet in entry["bullets"][:max_bullets]:
                lines.append(f"  > {bullet['text']}")
        lines.append("")

    oneliners = entries[detail:detail + oneliner]
    if oneliners:
        parts = []
        for entry in oneliners:
            short = entry["date"].split(" ")[0] if " " in entry["date"] else entry["date"]
            parts.append(f"{short} {entry['project']} ({entry['title']})")
        lines.append("Older: " + ", ".join(parts))
        lines.append("")

    projects = get_active_projects(entries)
    if projects:
        proj_parts = [f"{name} ({status})" for name, status in projects.items()]
        lines.append("Active projects: " + ", ".join(proj_parts))
        lines.append("")

    if len(lines) > 30:
        lines = lines[:30]

    return "\n".join(lines).rstrip()


# =============================================================================
# 6. Entry Management (add, update, validate)
# =============================================================================

def duplicate_check(entries: List[Dict], project: str, title: str) -> bool:
    """Check if the most recent entry is a likely duplicate."""
    if not entries:
        return False
    latest = entries[0]
    if latest["project"].lower() == project.lower():
        # Simple similarity: exact title match or high overlap
        if latest["title"].lower().strip() == title.lower().strip():
            return True
    return False


def validate_entry_bullets(bullets: List[str], quiet: bool = False) -> List[str]:
    """Validate bullet list, return warnings."""
    warnings: List[str] = []
    if not bullets:
        return warnings
    if len(bullets) < 1:
        warnings.append("Entry has no bullets")
    if len(bullets) > 8:
        warnings.append(f"Entry has {len(bullets)} bullets (recommended: 1-8)")

    for bullet in bullets:
        line = bullet if bullet.startswith("- ") else f"- {bullet}"
        m = TAG_RE.match(line)
        if m:
            tag = m.group(1).lower()
            if tag not in VALID_TAGS:
                warnings.append(f"Unknown tag [{tag}] in: {line}")
    return warnings


def validate_all_entries(entries: List[Dict]) -> List[Dict[str, Any]]:
    """Validate all entries, return list of issues."""
    issues: List[Dict[str, Any]] = []
    seen_headers: List[str] = []

    for i, entry in enumerate(entries):
        entry_issues: List[str] = []
        idx = i + 1

        # Check for missing fields
        if not entry["project"]:
            entry_issues.append("Missing project name")
        if not entry["title"]:
            entry_issues.append("Missing title")
        if not entry["date"]:
            entry_issues.append("Missing date")

        # Check bullet count
        bc = len(entry["bullets"])
        if bc == 0:
            entry_issues.append("No bullets")
        elif bc > 8:
            entry_issues.append(f"{bc} bullets (recommended max: 8)")

        # Check for unknown tags
        for b in entry["bullets"]:
            raw = b.get("raw", "")
            m = TAG_RE.match(raw)
            if m and m.group(1).lower() not in VALID_TAGS:
                entry_issues.append(f"Unknown tag [{m.group(1)}]")

        # Check for duplicate headers
        key = f"{entry['project']}|{entry['title']}"
        if key in seen_headers:
            entry_issues.append("Duplicate of another entry (same project + title)")
        seen_headers.append(key)

        if entry_issues:
            issues.append({
                "entry": idx,
                "date": entry["date"],
                "project": entry["project"],
                "title": entry["title"],
                "issues": entry_issues,
            })

    return issues


# =============================================================================
# 7. Search
# =============================================================================

def search_entries(
    entries: List[Dict],
    query: str,
    case_sensitive: bool = False,
    project_filter: Optional[str] = None,
    tag_filter: Optional[str] = None,
    since_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search entries for query string. Returns matching entries with match info."""
    results: List[Dict[str, Any]] = []
    q = query if case_sensitive else query.lower()

    for i, entry in enumerate(entries):
        # Apply filters
        if project_filter:
            if entry["project"].lower() != project_filter.lower():
                continue

        if tag_filter:
            entry_tags = {b["tag"] for b in entry["bullets"]}
            if tag_filter.lower() not in entry_tags:
                continue

        if since_filter:
            try:
                since_date = datetime.strptime(since_filter, "%Y-%m-%d")
                entry_date_str = entry["date"].split(" ")[0] if " " in entry["date"] else entry["date"]
                try:
                    entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d")
                    if entry_date < since_date:
                        continue
                except ValueError:
                    pass
            except ValueError:
                pass

        # Search in title, project, and bullet texts
        matches: List[str] = []
        searchable_title = entry["title"] if case_sensitive else entry["title"].lower()
        searchable_project = entry["project"] if case_sensitive else entry["project"].lower()

        if q in searchable_title:
            matches.append("title")
        if q in searchable_project:
            matches.append("project")

        for b in entry["bullets"]:
            searchable = b["text"] if case_sensitive else b["text"].lower()
            if q in searchable:
                matches.append(f"bullet:{b['tag']}")

        if matches:
            results.append({
                "index": i + 1,
                "entry": entry,
                "matches": matches,
            })

    return results


def highlight_match(text: str, query: str, case_sensitive: bool = False) -> str:
    """Highlight query matches in text with **bold** markers."""
    if not query:
        return text
    if case_sensitive:
        return text.replace(query, f"**{query}**")
    # Case-insensitive highlight — preserve original case
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"**{m.group(0)}**", text)


# =============================================================================
# 8. Archive
# =============================================================================

def archive_entries(entries: List[Dict], archive_path: Path) -> int:
    """Append entries to archive file. Returns count archived."""
    if not entries:
        return 0

    archive_path.parent.mkdir(parents=True, exist_ok=True)

    if archive_path.exists():
        existing = archive_path.read_text(encoding="utf-8").strip()
        # Find the end of the header line
        if existing.startswith("<!--"):
            header_end = existing.find("-->")
            if header_end >= 0:
                rest = existing[header_end + 3:].strip()
            else:
                rest = existing
        else:
            rest = existing
    else:
        rest = ""

    new_blocks = []
    for entry in entries:
        new_blocks.append("\n".join(entry["raw_lines"]))

    new_content = "\n\n".join(new_blocks)

    if rest:
        content = f"{ARCHIVE_HEADER}\n\n{new_content}\n\n{rest}\n"
    else:
        content = f"{ARCHIVE_HEADER}\n\n{new_content}\n"

    archive_path.write_text(content, encoding="utf-8")
    return len(entries)


def load_archive(archive_path: Path) -> List[Dict[str, Any]]:
    """Load and parse archive entries."""
    if not archive_path.exists():
        return []
    text = archive_path.read_text(encoding="utf-8")
    return parse_chronicle(text)


# =============================================================================
# 9. Export
# =============================================================================

def export_json(entries: List[Dict]) -> str:
    """Export entries as JSON."""
    data = [entry_to_dict(e) for e in entries]
    return json.dumps(data, indent=2, ensure_ascii=False)


def export_csv(entries: List[Dict]) -> str:
    """Export entries as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "project", "title", "tags", "bullets"])
    for entry in entries:
        tags = ", ".join(sorted({b["tag"] for b in entry["bullets"]}))
        bullets = " | ".join(b["text"] for b in entry["bullets"])
        writer.writerow([entry["date"], entry["project"], entry["title"], tags, bullets])
    return output.getvalue()


def export_markdown(entries: List[Dict]) -> str:
    """Export entries as clean markdown."""
    lines = []
    for entry in entries:
        lines.append(f"### {entry['date']} | {entry['project']} | {entry['title']}")
        for b in entry["bullets"]:
            lines.append(b["raw"])
        lines.append("")
    return "\n".join(lines)


# =============================================================================
# 10. Analytics
# =============================================================================

def compute_analytics(
    chronicle_entries: List[Dict],
    archive_entries: List[Dict],
) -> Dict[str, Any]:
    """Compute analytics across chronicle and archive entries."""
    all_entries = chronicle_entries + archive_entries
    total = len(all_entries)

    if total == 0:
        return {"total": 0, "chronicle": 0, "archive": 0}

    # Entries per project
    project_counts: Dict[str, int] = {}
    tag_counts: Dict[str, int] = {}
    total_bullets = 0
    dates: List[datetime] = []
    blocker_texts: List[str] = []
    decision_count = 0

    for entry in all_entries:
        proj = entry["project"]
        if proj:
            project_counts[proj] = project_counts.get(proj, 0) + 1

        for b in entry["bullets"]:
            total_bullets += 1
            tag_counts[b["tag"]] = tag_counts.get(b["tag"], 0) + 1
            if b["tag"] == "blocker":
                blocker_texts.append(b["text"])
            if b["tag"] == "decision":
                decision_count += 1

        # Parse date
        date_str = entry["date"].split(" ")[0] if " " in entry["date"] else entry["date"]
        try:
            dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
        except ValueError:
            pass

    avg_bullets = total_bullets / total if total > 0 else 0

    # Session frequency
    dates.sort()
    longest_gap_days = 0
    if len(dates) >= 2:
        for i in range(1, len(dates)):
            gap = (dates[i] - dates[i - 1]).days
            if gap > longest_gap_days:
                longest_gap_days = gap

    # Entries per day/week
    if len(dates) >= 2:
        span_days = max((dates[-1] - dates[0]).days, 1)
        entries_per_day = total / span_days
        entries_per_week = entries_per_day * 7
    else:
        entries_per_day = 0.0
        entries_per_week = 0.0

    # Most active projects (last 7 and 30 days)
    now = datetime.now()
    recent_7: Dict[str, int] = {}
    recent_30: Dict[str, int] = {}
    for entry in all_entries:
        date_str = entry["date"].split(" ")[0] if " " in entry["date"] else entry["date"]
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        proj = entry["project"]
        if not proj:
            continue
        if (now - d).days <= 7:
            recent_7[proj] = recent_7.get(proj, 0) + 1
        if (now - d).days <= 30:
            recent_30[proj] = recent_30.get(proj, 0) + 1

    return {
        "total": total,
        "chronicle": len(chronicle_entries),
        "archive": len(archive_entries),
        "project_counts": dict(sorted(project_counts.items(), key=lambda x: -x[1])),
        "tag_counts": dict(sorted(tag_counts.items(), key=lambda x: -x[1])),
        "avg_bullets": round(avg_bullets, 1),
        "entries_per_day": round(entries_per_day, 2),
        "entries_per_week": round(entries_per_week, 1),
        "longest_gap_days": longest_gap_days,
        "decision_count": decision_count,
        "blocker_count": len(blocker_texts),
        "most_active_7d": dict(sorted(recent_7.items(), key=lambda x: -x[1])),
        "most_active_30d": dict(sorted(recent_30.items(), key=lambda x: -x[1])),
    }


def format_ascii_bar(label: str, value: int, max_value: int, bar_width: int = 30) -> str:
    """Format a single ASCII bar chart row."""
    if max_value == 0:
        filled = 0
    else:
        filled = int((value / max_value) * bar_width)
    bar = "#" * filled + "." * (bar_width - filled)
    return f"  {label:<20} [{bar}] {value}"


# =============================================================================
# 11. CLI Command Handlers
# =============================================================================

def output_result(data: Any, text_fn: Any, args: argparse.Namespace) -> None:
    """Output either JSON or text based on flags."""
    use_json = getattr(args, "json", False)
    if not use_json:
        config = load_config(getattr(args, "config", None))
        use_json = config.get("json_output", False)

    if use_json:
        if isinstance(data, str):
            print(json.dumps({"output": data}, ensure_ascii=False))
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        result = text_fn()
        if result is not None:
            print(result)


def cmd_briefing(args: argparse.Namespace) -> None:
    """Generate a session briefing from the chronicle."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)
    if not path.exists():
        if getattr(args, "json", False):
            print(json.dumps({"briefing": None, "reason": "no chronicle file"}))
        return

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        if getattr(args, "json", False):
            print(json.dumps({"briefing": None, "reason": "empty chronicle"}))
        return

    entries = parse_chronicle(text)
    if not entries:
        if getattr(args, "json", False):
            print(json.dumps({"briefing": None, "reason": "no entries"}))
        return

    fmt = getattr(args, "format", None) or config.get("briefing_format", "auto")
    max_lines = config.get("briefing_max_lines", 25)

    if fmt == "structured":
        output = format_structured_briefing(entries, max_lines)
    elif fmt == "chronological":
        output = format_chronological_briefing(entries, args)
    else:
        if has_semantic_tags(entries):
            output = format_structured_briefing(entries, max_lines)
        else:
            output = format_chronological_briefing(entries, args)

    if getattr(args, "json", False) or config.get("json_output", False):
        sections = extract_sections(entries)
        data = {
            "briefing": output,
            "format": fmt,
            "entry_count": len(entries),
            "sections": {
                "active_threads": sections["active_threads"],
                "blockers": [{"text": t, "project": p} for t, p in sections["blockers"]],
                "decisions": sections["decisions"],
                "recent_work": [{"date": d, "project": p, "title": t} for d, p, t in sections["recent_work"]],
                "focus": sections["focus"],
            },
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif output:
        print(output)


def cmd_add(args: argparse.Namespace) -> None:
    """Add a new entry to the chronicle."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)
    path.parent.mkdir(parents=True, exist_ok=True)

    quiet = getattr(args, "quiet", False)
    verbose = getattr(args, "verbose", False)
    use_json = getattr(args, "json", False) or config.get("json_output", False)

    # Validate bullets
    warnings: List[str] = []
    if args.bullets:
        warnings = validate_entry_bullets(args.bullets, quiet)
        if warnings and not quiet:
            for w in warnings:
                if not use_json:
                    print(f"Warning: {w}", file=sys.stderr)

    # Duplicate check
    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
        existing_entries = parse_chronicle(text)
        if duplicate_check(existing_entries, args.project, args.title):
            warnings.append("Possible duplicate of most recent entry (same project + title)")
            if not quiet and not use_json:
                print(f"Warning: {warnings[-1]}", file=sys.stderr)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header_line = f"### {now} | {args.project} | {args.title}"

    entry_lines = [header_line]
    if args.bullets:
        for bullet in args.bullets:
            if not bullet.startswith("- "):
                bullet = f"- {bullet}"
            entry_lines.append(bullet)

    new_entry = "\n".join(entry_lines)

    max_entries = getattr(args, "max_entries", None) or config.get("max_entries", 20)

    with FileLock(path):
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
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
        do_rotate(path, max_entries, config, args)

    if use_json:
        print(json.dumps({
            "action": "added",
            "project": args.project,
            "title": args.title,
            "date": now,
            "warnings": warnings,
        }, ensure_ascii=False))
    elif not quiet:
        print(f"Added: {args.project} | {args.title}")


def cmd_update(args: argparse.Namespace) -> None:
    """Update an existing chronicle entry."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)
    use_json = getattr(args, "json", False) or config.get("json_output", False)
    quiet = getattr(args, "quiet", False)

    if not path.exists():
        msg = "No chronicle file found."
        if use_json:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        return

    with FileLock(path):
        text = path.read_text(encoding="utf-8")
        entries = parse_chronicle(text)

        idx = args.entry - 1  # Convert to 0-indexed
        if idx < 0 or idx >= len(entries):
            msg = f"Entry {args.entry} not found (have {len(entries)} entries)"
            if use_json:
                print(json.dumps({"error": msg}))
            else:
                print(msg)
            return

        entry = entries[idx]
        changes: List[str] = []

        # Set title
        if args.set_title:
            old_header_line = entry["raw_lines"][0]
            parts = [p.strip() for p in old_header_line[4:].split("|")]
            if len(parts) >= 3:
                parts[2] = args.set_title
            new_header_line = "### " + " | ".join(parts)
            entry["raw_lines"][0] = new_header_line
            entry["title"] = args.set_title
            entry["header"] = " | ".join(parts)
            changes.append(f"title -> {args.set_title}")

        # Add bullet
        if args.add_bullet:
            bullet = args.add_bullet
            if not bullet.startswith("- "):
                bullet = f"- {bullet}"
            entry["raw_lines"].append(bullet)
            entry["bullets"].append(parse_bullet(bullet))
            changes.append(f"added bullet: {bullet}")

        # Add tag shorthand
        if args.add_tag:
            tag = args.add_tag[0]
            text_val = args.add_tag[1]
            if tag.lower() not in VALID_TAGS:
                warn = f"Unknown tag [{tag}] (known: {', '.join(sorted(VALID_TAGS))})"
                if not quiet:
                    if use_json:
                        pass  # Include in output
                    else:
                        print(f"Warning: {warn}", file=sys.stderr)
            bullet = f"- [{tag}] {text_val}"
            entry["raw_lines"].append(bullet)
            entry["bullets"].append(parse_bullet(bullet))
            changes.append(f"added [{tag}] {text_val}")

        if not changes:
            msg = "No changes specified (use --add-bullet, --set-title, or --add-tag)"
            if use_json:
                print(json.dumps({"error": msg}))
            else:
                print(msg)
            return

        # Rebuild and save
        content = rebuild_chronicle(entries)
        path.write_text(content, encoding="utf-8")

    if use_json:
        print(json.dumps({
            "action": "updated",
            "entry": args.entry,
            "changes": changes,
            "project": entry["project"],
            "title": entry["title"],
        }, ensure_ascii=False))
    elif not quiet:
        print(f"Updated entry {args.entry}: {', '.join(changes)}")


def do_rotate(
    path: Path,
    max_entries: int = 20,
    config: Optional[Dict] = None,
    args: Optional[argparse.Namespace] = None,
) -> int:
    """Trim chronicle to max_entries. Archive removed entries if enabled.

    Returns count of removed entries.
    """
    text = path.read_text(encoding="utf-8")
    entries = parse_chronicle(text)

    if len(entries) <= max_entries:
        return 0

    kept = entries[:max_entries]
    removed = entries[max_entries:]
    removed_count = len(removed)

    # Archive removed entries if enabled
    archive_enabled = True
    if config:
        archive_enabled = config.get("archive_enabled", True)

    if archive_enabled and removed:
        archive_path = get_archive_path(path)
        archive_entries(removed, archive_path)

    # Rebuild file
    content = rebuild_chronicle(kept)
    path.write_text(content, encoding="utf-8")

    quiet = False
    if args:
        quiet = getattr(args, "quiet", False)

    if removed_count > 0 and not quiet:
        verb = "archived" if archive_enabled else "removed"
        print(f"Rotated: {verb} {removed_count} oldest entries, kept {max_entries}")

    return removed_count


def cmd_rotate(args: argparse.Namespace) -> None:
    """Manually rotate the chronicle."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)
    use_json = getattr(args, "json", False) or config.get("json_output", False)

    if not path.exists():
        msg = "No chronicle file found."
        if use_json:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        return

    max_entries = getattr(args, "max_entries", None) or config.get("max_entries", 20)

    with FileLock(path):
        removed = do_rotate(path, max_entries, config, args)

    if use_json:
        text = path.read_text(encoding="utf-8")
        entries = parse_chronicle(text)
        print(json.dumps({
            "action": "rotate",
            "removed": removed,
            "remaining": len(entries),
            "max_entries": max_entries,
        }))
    else:
        # Show status after
        cmd_status(args)


def cmd_search(args: argparse.Namespace) -> None:
    """Search across chronicle and/or archive."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)
    use_json = getattr(args, "json", False) or config.get("json_output", False)
    archive_only = getattr(args, "archive_only", False)
    case_sensitive = getattr(args, "case_sensitive", False)

    query = args.query

    all_results: List[Dict[str, Any]] = []

    # Search chronicle
    if not archive_only and path.exists():
        text = path.read_text(encoding="utf-8")
        entries = parse_chronicle(text)
        results = search_entries(
            entries, query,
            case_sensitive=case_sensitive,
            project_filter=getattr(args, "project", None),
            tag_filter=getattr(args, "tag", None),
            since_filter=getattr(args, "since", None),
        )
        for r in results:
            r["source"] = "chronicle"
            all_results.append(r)

    # Search archive
    archive_path = get_archive_path(path)
    if archive_path.exists():
        archive = load_archive(archive_path)
        results = search_entries(
            archive, query,
            case_sensitive=case_sensitive,
            project_filter=getattr(args, "project", None),
            tag_filter=getattr(args, "tag", None),
            since_filter=getattr(args, "since", None),
        )
        for r in results:
            r["source"] = "archive"
            all_results.append(r)

    if use_json:
        output = []
        for r in all_results:
            output.append({
                "source": r["source"],
                "index": r["index"],
                "matches": r["matches"],
                "entry": entry_to_dict(r["entry"]),
            })
        print(json.dumps({"query": query, "count": len(output), "results": output}, indent=2, ensure_ascii=False))
    else:
        if not all_results:
            print(f"No results for: {query}")
            return

        print(f"Found {len(all_results)} result(s) for: {query}\n")
        for r in all_results:
            e = r["entry"]
            source_tag = f" [{r['source']}]" if r["source"] == "archive" else ""
            title = highlight_match(e["title"], query, case_sensitive)
            print(f"  #{r['index']}{source_tag} {e['date']} | {e['project']} | {title}")
            for b in e["bullets"]:
                text_hl = highlight_match(b["text"], query, case_sensitive)
                if text_hl != b["text"]:
                    print(f"    - [{b['tag']}] {text_hl}")
            print()


def cmd_archive(args: argparse.Namespace) -> None:
    """Show archive stats or restore an entry."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)
    archive_path = get_archive_path(path)
    use_json = getattr(args, "json", False) or config.get("json_output", False)
    quiet = getattr(args, "quiet", False)

    restore_idx = getattr(args, "restore", None)

    if restore_idx is not None:
        # Restore entry from archive to chronicle
        if not archive_path.exists():
            msg = "No archive file found."
            if use_json:
                print(json.dumps({"error": msg}))
            else:
                print(msg)
            return

        archive = load_archive(archive_path)
        idx = restore_idx - 1  # Convert to 0-indexed

        if idx < 0 or idx >= len(archive):
            msg = f"Archive entry {restore_idx} not found (have {len(archive)} entries)"
            if use_json:
                print(json.dumps({"error": msg}))
            else:
                print(msg)
            return

        entry = archive[idx]

        with FileLock(path):
            # Add to chronicle
            if path.exists():
                text = path.read_text(encoding="utf-8").strip()
                lines = text.split("\n", 1)
                file_header = lines[0] if lines[0].startswith("<!--") else CHRONICLE_HEADER
                rest = lines[1].strip() if len(lines) > 1 else ""
                if not lines[0].startswith("<!--"):
                    rest = text

                entry_text = "\n".join(entry["raw_lines"])
                content = f"{file_header}\n\n{entry_text}\n\n{rest}\n"
            else:
                entry_text = "\n".join(entry["raw_lines"])
                content = f"{CHRONICLE_HEADER}\n\n{entry_text}\n"

            path.write_text(content, encoding="utf-8")

        # Remove from archive
        with FileLock(archive_path):
            remaining = [e for i, e in enumerate(archive) if i != idx]
            if remaining:
                archive_content = rebuild_chronicle(remaining, ARCHIVE_HEADER)
            else:
                archive_content = f"{ARCHIVE_HEADER}\n"
            archive_path.write_text(archive_content, encoding="utf-8")

        if use_json:
            print(json.dumps({
                "action": "restored",
                "entry": restore_idx,
                "project": entry["project"],
                "title": entry["title"],
                "date": entry["date"],
            }, ensure_ascii=False))
        elif not quiet:
            print(f"Restored: {entry['date']} | {entry['project']} | {entry['title']}")
        return

    # Show archive stats
    if not archive_path.exists():
        if use_json:
            print(json.dumps({"exists": False, "entries": 0}))
        else:
            print("No archive file found.")
        return

    archive = load_archive(archive_path)
    size = archive_path.stat().st_size

    if use_json:
        data = {
            "exists": True,
            "path": str(archive_path),
            "entries": len(archive),
            "size_bytes": size,
            "entries_list": [entry_to_dict(e) for e in archive],
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Archive: {archive_path}")
        print(f"Entries: {len(archive)}")
        print(f"File size: {size} bytes")
        if archive:
            print()
            for i, entry in enumerate(archive):
                print(f"  {i + 1}. {entry['date']} | {entry['project']} | {entry['title']}")


def cmd_export(args: argparse.Namespace) -> None:
    """Export chronicle (and optionally archive) in various formats."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)

    if not path.exists():
        print("No chronicle file found.", file=sys.stderr)
        return

    text = path.read_text(encoding="utf-8")
    entries = parse_chronicle(text)

    # Include archive if requested
    if getattr(args, "include_archive", False):
        archive_path = get_archive_path(path)
        if archive_path.exists():
            archive = load_archive(archive_path)
            entries.extend(archive)

    # Filter by project
    project_filter = getattr(args, "project", None)
    if project_filter:
        entries = [e for e in entries if e["project"].lower() == project_filter.lower()]

    fmt = getattr(args, "format", "json") or "json"

    if fmt == "json":
        print(export_json(entries))
    elif fmt == "csv":
        print(export_csv(entries), end="")
    elif fmt == "markdown":
        print(export_markdown(entries))


def cmd_analytics(args: argparse.Namespace) -> None:
    """Show detailed analytics."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)
    use_json = getattr(args, "json", False) or config.get("json_output", False)

    chronicle_entries: List[Dict] = []
    archive_list: List[Dict] = []

    if path.exists():
        text = path.read_text(encoding="utf-8")
        chronicle_entries = parse_chronicle(text)

    archive_path = get_archive_path(path)
    if archive_path.exists():
        archive_list = load_archive(archive_path)

    stats = compute_analytics(chronicle_entries, archive_list)

    if use_json:
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    if stats["total"] == 0:
        print("No entries found.")
        return

    print("=== Session Chronicle Analytics ===\n")
    print(f"Total entries:   {stats['total']} (chronicle: {stats['chronicle']}, archive: {stats['archive']})")
    print(f"Avg bullets/entry: {stats['avg_bullets']}")
    print(f"Session frequency: {stats['entries_per_day']}/day ({stats['entries_per_week']}/week)")
    print(f"Longest gap:     {stats['longest_gap_days']} days")
    print(f"Decisions:       {stats['decision_count']}")
    print(f"Blockers:        {stats['blocker_count']}")
    print()

    # Project distribution
    if stats["project_counts"]:
        print("Entries per project:")
        max_val = max(stats["project_counts"].values()) if stats["project_counts"] else 1
        for proj, count in stats["project_counts"].items():
            print(format_ascii_bar(proj, count, max_val))
        print()

    # Tag distribution
    if stats["tag_counts"]:
        print("Tag distribution:")
        max_val = max(stats["tag_counts"].values()) if stats["tag_counts"] else 1
        for tag, count in stats["tag_counts"].items():
            print(format_ascii_bar(tag, count, max_val))
        print()

    # Most active projects
    if stats["most_active_7d"]:
        parts = [f"{p} ({c})" for p, c in stats["most_active_7d"].items()]
        print(f"Most active (7d):  {', '.join(parts)}")
    if stats["most_active_30d"]:
        parts = [f"{p} ({c})" for p, c in stats["most_active_30d"].items()]
        print(f"Most active (30d): {', '.join(parts)}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate all chronicle entries for issues."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)
    use_json = getattr(args, "json", False) or config.get("json_output", False)

    if not path.exists():
        msg = "No chronicle file found."
        if use_json:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        return

    text = path.read_text(encoding="utf-8")
    entries = parse_chronicle(text)
    issues = validate_all_entries(entries)

    if use_json:
        print(json.dumps({
            "total_entries": len(entries),
            "entries_with_issues": len(issues),
            "issues": issues,
        }, indent=2, ensure_ascii=False))
        return

    if not issues:
        print(f"All {len(entries)} entries valid.")
        return

    print(f"Found issues in {len(issues)} of {len(entries)} entries:\n")
    for issue in issues:
        print(f"  Entry {issue['entry']}: {issue['date']} | {issue['project']} | {issue['title']}")
        for problem in issue["issues"]:
            print(f"    - {problem}")
        print()


def cmd_config(args: argparse.Namespace) -> None:
    """Show or modify configuration."""
    config_path = getattr(args, "config", None)
    use_json = getattr(args, "json", False)

    if getattr(args, "reset", False):
        save_config(DEFAULT_CONFIG, config_path)
        if use_json:
            print(json.dumps({"action": "reset", "config": DEFAULT_CONFIG}))
        else:
            print("Config reset to defaults.")
        return

    if getattr(args, "set", None):
        key, value = args.set
        config = load_config(config_path)
        if key not in DEFAULT_CONFIG:
            print(f"Unknown config key: {key} (known: {', '.join(DEFAULT_CONFIG.keys())})", file=sys.stderr)
            return

        # Cast value to the right type based on defaults
        default_val = DEFAULT_CONFIG[key]
        if isinstance(default_val, bool):
            value = value.lower() in ("true", "1", "yes")
        elif isinstance(default_val, int):
            try:
                value = int(value)
            except ValueError:
                print(f"Invalid integer: {value}", file=sys.stderr)
                return

        config[key] = value
        save_config(config, config_path)
        if use_json:
            print(json.dumps({"action": "set", "key": key, "value": value}))
        else:
            print(f"Set {key} = {value}")
        return

    # Show current config
    config = load_config(config_path)
    actual_path = get_config_path(config_path)

    if use_json:
        print(json.dumps({"path": str(actual_path), "config": config}, indent=2, ensure_ascii=False))
    else:
        print(f"Config: {actual_path}")
        exists = actual_path.exists()
        print(f"Exists: {exists}")
        print()
        for k, v in config.items():
            default_marker = "" if config.get(k) != DEFAULT_CONFIG.get(k) else " (default)"
            print(f"  {k}: {v}{default_marker}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show chronicle status."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)
    use_json = getattr(args, "json", False) or config.get("json_output", False)

    if use_json:
        data: Dict[str, Any] = {"path": str(path), "exists": path.exists()}
        if path.exists():
            text = path.read_text(encoding="utf-8")
            entries = parse_chronicle(text)
            data["entries"] = len(entries)
            data["size_bytes"] = path.stat().st_size
            if entries:
                data["latest"] = entry_to_dict(entries[0])
                if len(entries) > 1:
                    data["oldest"] = entry_to_dict(entries[-1])
                data["active_projects"] = list(get_active_projects(entries).keys())
            # Archive info
            archive_path = get_archive_path(path)
            if archive_path.exists():
                archive = load_archive(archive_path)
                data["archive_entries"] = len(archive)
                data["archive_size_bytes"] = archive_path.stat().st_size
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    print(f"Chronicle: {path}")

    if not path.exists():
        print("Status: not initialized")
        print("Run: chronicle-manager.py init")
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

    # Archive info
    archive_path = get_archive_path(path)
    if archive_path.exists():
        archive = load_archive(archive_path)
        print(f"Archive: {len(archive)} entries ({archive_path.stat().st_size} bytes)")


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize the chronicle file and directory."""
    config = load_config(getattr(args, "config", None))
    path = get_chronicle_path(args, config)
    use_json = getattr(args, "json", False) or config.get("json_output", False)

    if path.exists():
        if use_json:
            print(json.dumps({"action": "init", "status": "already_exists", "path": str(path)}))
        else:
            print(f"Chronicle already exists at {path}")
            cmd_status(args)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{CHRONICLE_HEADER}\n", encoding="utf-8")

    if use_json:
        print(json.dumps({"action": "init", "status": "created", "path": str(path)}))
    else:
        print(f"Initialized: {path}")


# =============================================================================
# 12. CLI Argument Parsing and Main
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    # Parent parser with global flags — inherited by all subcommands
    global_parser = argparse.ArgumentParser(add_help=False)
    global_parser.add_argument("--json", action="store_true", default=False, help="JSON output for any command")
    global_parser.add_argument("--quiet", action="store_true", default=False, help="Suppress non-essential output")
    global_parser.add_argument("--verbose", action="store_true", default=False, help="Extra debug info")
    global_parser.add_argument("--config", type=str, default=None, help="Use alternate config file path")
    global_parser.add_argument("--chronicle", type=str, default=None, help="Override chronicle file path")

    parser = argparse.ArgumentParser(
        description="Session Chronicle Manager v2.0 — cross-tool session coherence",
        epilog="Examples:\n"
               "  chronicle-manager.py add --project myapp --title 'Fixed auth'\n"
               "  chronicle-manager.py search 'JWT' --project myapp\n"
               "  chronicle-manager.py analytics\n"
               "  chronicle-manager.py export --format json --include-archive\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[global_parser],
    )
    parser.add_argument("--version", action="version", version=f"session-coherence {VERSION}")

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # briefing
    p_brief = sub.add_parser(
        "briefing",
        help="Generate session briefing",
        description="Generate a session briefing from the chronicle. Auto-detects format based on tag usage.",
        parents=[global_parser],
    )
    p_brief.add_argument("--format", choices=["auto", "structured", "chronological"],
                         default="auto", help="Briefing format (default: auto)")
    p_brief.add_argument("--detail", type=int, default=5, help="Detailed entries count (default: 5)")
    p_brief.add_argument("--oneliner", type=int, default=10, help="One-liner entries count (default: 10)")
    p_brief.add_argument("--max-bullets", type=int, default=3, help="Max bullets per entry (default: 3)")

    # add
    p_add = sub.add_parser(
        "add",
        help="Add a session entry",
        description="Add a new entry to the top of the chronicle. Auto-rotates if over max entries.",
        epilog='Example: add --project myapp --title "Fixed login" --bullets "- [fix] Resolved OAuth" "- [next] Deploy"',
        parents=[global_parser],
    )
    p_add.add_argument("--project", required=True, help="Project name")
    p_add.add_argument("--title", required=True, help="Short session title")
    p_add.add_argument("--bullets", nargs="*", help="Bullet points (use quotes)")
    p_add.add_argument("--max-entries", type=int, default=None, help="Max entries to keep (default: from config or 20)")

    # update
    p_update = sub.add_parser(
        "update",
        help="Update an existing entry",
        description="Modify an existing chronicle entry by index (1-indexed from top/newest).",
        epilog='Example: update --entry 1 --add-bullet "- [status] Now complete"',
        parents=[global_parser],
    )
    p_update.add_argument("--entry", type=int, required=True, help="Entry number (1-indexed from newest)")
    p_update.add_argument("--add-bullet", type=str, default=None, help="Add a bullet to the entry")
    p_update.add_argument("--set-title", type=str, default=None, help="Change the entry title")
    p_update.add_argument("--add-tag", nargs=2, metavar=("TAG", "TEXT"), default=None,
                          help="Add a tagged bullet shorthand, e.g. --add-tag blocker 'API pending'")

    # rotate
    p_rot = sub.add_parser(
        "rotate",
        help="Trim old entries (archives removed entries)",
        description="Remove oldest entries beyond max. Archived entries are saved to archive.md.",
        parents=[global_parser],
    )
    p_rot.add_argument("--max-entries", type=int, default=None, help="Max entries to keep (default: from config or 20)")

    # search
    p_search = sub.add_parser(
        "search",
        help="Search chronicle and archive",
        description="Full-text search across chronicle and archive entries.",
        epilog='Example: search "JWT" --project myapp --tag decision --since 2026-01-01',
        parents=[global_parser],
    )
    p_search.add_argument("query", type=str, help="Search query text")
    p_search.add_argument("--project", type=str, default=None, help="Filter by project name")
    p_search.add_argument("--tag", type=str, default=None, help="Filter by tag (decision, blocker, etc.)")
    p_search.add_argument("--since", type=str, default=None, help="Filter entries since date (YYYY-MM-DD)")
    p_search.add_argument("--case-sensitive", action="store_true", default=False, help="Case-sensitive search")
    p_search.add_argument("--archive-only", action="store_true", default=False, help="Search only archive")

    # archive
    p_archive = sub.add_parser(
        "archive",
        help="Show archive stats or restore entries",
        description="View archived entries or restore one back to the chronicle.",
        epilog="Example: archive --restore 3",
        parents=[global_parser],
    )
    p_archive.add_argument("--restore", type=int, default=None, metavar="N",
                           help="Restore entry N from archive back to chronicle")

    # export
    p_export = sub.add_parser(
        "export",
        help="Export chronicle in various formats",
        description="Export chronicle entries as JSON, CSV, or Markdown.",
        epilog="Example: export --format json --include-archive --project myapp",
        parents=[global_parser],
    )
    p_export.add_argument("--format", choices=["json", "csv", "markdown"], default="json",
                          help="Export format (default: json)")
    p_export.add_argument("--include-archive", action="store_true", default=False,
                          help="Include archived entries")
    p_export.add_argument("--project", type=str, default=None, help="Filter by project name")

    # analytics
    sub.add_parser(
        "analytics",
        help="Show detailed statistics",
        description="Compute and display analytics across chronicle and archive entries.",
        parents=[global_parser],
    )

    # validate
    sub.add_parser(
        "validate",
        help="Check entries for issues",
        description="Validate all chronicle entries for missing fields, unknown tags, duplicates, etc.",
        parents=[global_parser],
    )

    # config
    p_config = sub.add_parser(
        "config",
        help="Show or modify configuration",
        description="View current config, set values, or reset to defaults.",
        epilog="Example: config --set max_entries 30",
        parents=[global_parser],
    )
    p_config.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), default=None,
                          help="Set a config value")
    p_config.add_argument("--reset", action="store_true", default=False, help="Reset config to defaults")

    # status
    sub.add_parser(
        "status",
        help="Show chronicle status",
        description="Display chronicle file info, entry count, and active projects.",
        parents=[global_parser],
    )

    # init
    sub.add_parser(
        "init",
        help="Initialize chronicle file",
        description="Create the chronicle file and directory if they don't exist.",
        parents=[global_parser],
    )

    return parser


def main() -> None:
    """Entry point."""
    # Fix Unicode output on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "briefing": cmd_briefing,
        "add": cmd_add,
        "update": cmd_update,
        "rotate": cmd_rotate,
        "search": cmd_search,
        "archive": cmd_archive,
        "export": cmd_export,
        "analytics": cmd_analytics,
        "validate": cmd_validate,
        "config": cmd_config,
        "status": cmd_status,
        "init": cmd_init,
    }

    try:
        commands[args.command](args)
    except TimeoutError as e:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
