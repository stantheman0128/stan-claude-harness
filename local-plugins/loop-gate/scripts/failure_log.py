"""loop-gate PostToolUseFailure hook：記錄工具失敗，當 Loop 4 檢討與 hookify 的素材。"""
import json
import sys
import time

import hook_health

MAX_BYTES = 2_000_000


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    path = hook_health.state_dir() / "tool-failures.jsonl"
    hook_health._rotate(path, MAX_BYTES)
    error = event.get("error") or event.get("tool_response") or ""
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "session_id": str(event.get("session_id", "")),
        "tool_name": str(event.get("tool_name", "")),
        "error": str(error)[:500],
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    sys.exit(0)


if __name__ == "__main__":
    hook_health.guard("failure_log", main)
