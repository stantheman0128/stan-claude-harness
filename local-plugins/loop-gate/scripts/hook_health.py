"""loop-gate 共用：hook 失效要大聲（fail loud），gate 不准鎖死使用者（fail open）。

所有路徑尊重 LOOP_GATE_HOME 環境變數，讓 selftest 能完全隔離。
"""
import json
import os
import sys
import time
import traceback
from pathlib import Path

MAX_LOG_BYTES = 1_000_000


def home_dir():
    override = os.environ.get("LOOP_GATE_HOME")
    return Path(override) if override else Path.home() / ".claude"


def state_dir():
    d = home_dir() / "loop-gate"
    d.mkdir(parents=True, exist_ok=True)
    return d


def health_log_path():
    return home_dir() / "hook-health.log"


def _rotate(path, limit):
    try:
        if path.exists() and path.stat().st_size > limit:
            old = path.with_name(path.name + ".old")
            if old.exists():
                old.unlink()
            path.rename(old)
    except OSError:
        pass


def log_failure(hook, error):
    try:
        path = health_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _rotate(path, MAX_LOG_BYTES)
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "hook": hook,
            "error": str(error)[:1000],
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass  # health 機制本身失敗時保持沉默，不准反過來弄掛 hook


NOTICE_TTL_SEC = 7 * 24 * 3600


def once_per_session(kind, session_id, key):
    """同一 session 對同一 key 只回 True 一次，用來讓使用者看得到的提醒不重複出現。

    紀錄存在 state_dir()/notices.json，超過 7 天的自動清掉。
    """
    path = state_dir() / "notices.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    now = time.time()
    data = {k: v for k, v in data.items()
            if isinstance(v, (int, float)) and now - v <= NOTICE_TTL_SEC}
    token = f"{kind}|{session_id}|{key}"
    if token in data:
        return False
    data[token] = now
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return True


def emit_json(obj):
    """stdout 只印一個 JSON 物件；用 ASCII 跳脫，避開 Windows 主控台編碼把中文弄壞。"""
    sys.stdout.write(json.dumps(obj, ensure_ascii=True) + "\n")


def guard(hook_name, main):
    try:
        main()
        sys.exit(0)
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 - 這裡就是要接住一切
        log_failure(hook_name, traceback.format_exc(limit=5))
        sys.exit(0)
