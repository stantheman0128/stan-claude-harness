#!/usr/bin/env python3
"""SessionStart watcher for skills and router-miss feedback."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


CLAUDE = Path.home() / ".claude"
SETTINGS = CLAUDE / "settings.json"
SKILLS = CLAUDE / "skills"
SNAP = CLAUDE / "skill-routing-snapshot.json"


def safe_session_name(session: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(session))


def current_state() -> dict[str, list[str]]:
    plugins, overridden_off = [], set()
    try:
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        plugins = sorted(key for key, value in (data.get("enabledPlugins") or {}).items() if value is True)
        overridden_off = {key for key, value in (data.get("skillOverrides") or {}).items() if value == "off"}
    except Exception:
        pass
    personal: list[str] = []
    try:
        personal = sorted(path.name for path in SKILLS.iterdir()
                          if path.is_dir() and (path / "SKILL.md").exists() and path.name not in overridden_off)
    except Exception:
        pass
    return {"plugins": plugins, "personal": personal}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        return []
    return records


def misses_for_session(usage: Path, session: str) -> list[dict[str, Any]]:
    """Prefer the atomic per-session file; retain read-only legacy fallback."""
    session_path = usage / f"misses-{safe_session_name(session)}.jsonl"
    if session_path.exists():
        return read_jsonl(session_path)
    return [record for record in read_jsonl(usage / "misses.jsonl") if record.get("session") == session]


def banner() -> str:
    recent: list[str] = []
    usage = CLAUDE / "skill-usage"
    try:
        files = sorted(usage.glob("session-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for path in files[:4]:
            recent.extend(json.loads(path.read_text(encoding="utf-8")).get("skills_used") or [])
    except Exception:
        files = []
    seen: set[str] = set()
    unique = [skill for skill in recent if not (skill in seen or seen.add(skill))]
    tail = ("；近期用過：" + "、".join(unique[:6])) if unique else "；近期未載入任何 skill"

    miss_tail = ""
    try:
        if files:
            last = json.loads(files[0].read_text(encoding="utf-8"))
            if last.get("router_misses"):
                misses = misses_for_session(usage, str(last.get("session") or ""))
                names = [
                    "/".join(record.get("skills", [])) + ("(強制)" if record.get("zone") == "mandatory" else "")
                    for record in misses
                ]
                miss_tail = ("；⚠️ 上次 router 建議未被載入：" + "、".join(names[:4])) if names else \
                    ("；⚠️ 上次 router 失手 %d 次" % last["router_misses"])
    except Exception:
        pass
    return (
        "⚙️ [skill 系統啟用中] 關鍵字提醒(UserPromptSubmit) + 用量紀錄(Stop) + 失手對帳(misses) 運作中"
        + tail + miss_tail
        + "。（請在本 session 第一則回覆開頭把這行顯示給使用者一次，讓他確認系統在跑；之後不必重複。）"
    )


def main() -> int:
    current = current_state()
    try:
        previous = json.loads(SNAP.read_text(encoding="utf-8")) if SNAP.exists() else None
    except Exception:
        previous = None
    try:
        SNAP.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    print(banner())
    if previous is None:
        return 0
    new_plugins = [item for item in current["plugins"] if item not in set(previous.get("plugins", []))]
    new_personal = [item for item in current["personal"] if item not in set(previous.get("personal", []))]
    removed_plugins = [item for item in previous.get("plugins", []) if item not in set(current["plugins"])]
    removed_personal = [item for item in previous.get("personal", []) if item not in set(current["personal"])]
    if not (new_plugins or new_personal or removed_plugins or removed_personal):
        return 0
    lines = ["[skill-routing watch] 偵測到自上次 session 以來的 skill / plugin 變動："]
    if new_plugins:
        lines.append("  新啟用 plugin：" + ", ".join(new_plugins))
    if new_personal:
        lines.append("  新個人 skill：" + ", ".join(new_personal))
    if removed_plugins:
        lines.append("  移除/停用 plugin：" + ", ".join(removed_plugins))
    if removed_personal:
        lines.append("  移除/停用個人 skill：" + ", ".join(removed_personal))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
