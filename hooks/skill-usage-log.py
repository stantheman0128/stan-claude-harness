#!/usr/bin/env python3
"""Stop hook: write one atomic skill-usage and miss record per Claude session.

Do not append router misses to a shared JSONL. Multiple Stop hooks can finish at
the same time on Windows, and a shared append file has no useful ownership or
atomicity boundary. A session owns `misses-<session>.jsonl`, so replacing that
file atomically is both idempotent and safe across concurrent sessions.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


DEFAULT_OUT_DIR = Path.home() / ".claude" / "skill-usage"


def safe_session_name(session: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(session))


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        # NTFS can transiently reject a replacement while another Stop hook is
        # completing a replacement of the same session snapshot. The temp file
        # is unique; retrying the final atomic replace keeps the last complete
        # snapshot without ever exposing a partial JSON/JSONL file.
        for attempt in range(12):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 11:
                    raise
                time.sleep(min(0.005 * (2 ** attempt), 0.1))
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def atomic_write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records))


def skill_uses_from(content: Any) -> list[str]:
    found: list[str] = []
    if not isinstance(content, list):
        return found
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and str(block.get("name", "")).split("__")[-1] == "Skill":
            tool_input = block.get("input") or {}
            name = tool_input.get("skill") or tool_input.get("name") or tool_input.get("command")
            if name:
                found.append(str(name))
    return found


def skills_from_transcript(transcript: Path) -> list[str]:
    used: list[str] = []
    with transcript.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(event, dict):
                continue
            message = event.get("message") if isinstance(event.get("message"), dict) else event
            used.extend(skill_uses_from(message.get("content") if isinstance(message, dict) else None))
    seen: set[str] = set()
    return [skill for skill in used if not (skill in seen or seen.add(skill))]


def calculate_misses(suggestions_path: Path, used: list[str]) -> tuple[list[dict[str, Any]], int]:
    misses: list[dict[str, Any]] = []
    mandatory_misses = 0
    if not suggestions_path.exists():
        return misses, mandatory_misses
    used_set = set(used)
    seen_keys: set[str] = set()
    for line in suggestions_path.read_text(encoding="utf-8").splitlines():
        try:
            suggestion = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(suggestion, dict):
            continue
        raw_skills = suggestion.get("skills", [])
        if not isinstance(raw_skills, list):
            continue
        skills = [skill for skill in raw_skills if isinstance(skill, str) and skill and skill != "graphify"]
        if not skills:
            continue
        key = "|".join(skills)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if any(skill in used_set for skill in skills):
            continue
        miss = {"zone": suggestion.get("zone", "?"), "skills": skills}
        misses.append(miss)
        if miss["zone"] == "mandatory":
            mandatory_misses += 1
    return misses, mandatory_misses


def process_session(transcript_path: Path, session: str, out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any] | None:
    """Rebuild one session's ground-truth files. Safe to call more than once."""
    if not transcript_path.exists():
        return None
    safe = safe_session_name(session)
    used = skills_from_transcript(transcript_path)
    misses, mandatory_misses = calculate_misses(out_dir / f"suggestions-{safe}.jsonl", used)
    miss_records = [{"session": session, **miss} for miss in misses]

    # This replaces only this session's file. An empty file deliberately clears a
    # stale prior result if a later Stop run observes that the skill was loaded.
    misses_file = f"misses-{safe}.jsonl"
    atomic_write_jsonl(out_dir / misses_file, miss_records)
    summary = {
        "schema_version": 2,
        "session": session,
        "count": len(used),
        "skills_used": used,
        "router_misses": len(misses),
        "router_mandatory_misses": mandatory_misses,
        "misses_file": misses_file,
    }
    atomic_write_json(out_dir / f"session-{safe}.json", summary)
    return summary


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    transcript = data.get("transcript_path")
    session = str(data.get("session_id") or "default")
    if transcript:
        process_session(Path(transcript), session)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Hooks must never prevent a user session from closing.
    sys.exit(0)
