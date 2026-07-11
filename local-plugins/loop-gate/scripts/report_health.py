"""loop-gate SessionStart hook：上個 24h 有 hook 失敗就回報一行進 context（fail-loud 的出口）。"""
import json
import sys
import time

import hook_health

WINDOW_SEC = 24 * 3600


def main():
    sys.stdin.read()  # 消化 event，內容不需要
    path = hook_health.health_log_path()
    if not path.exists():
        sys.exit(0)
    now = time.time()
    recent = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
            ts = time.mktime(time.strptime(entry["ts"], "%Y-%m-%dT%H:%M:%S"))
        except (ValueError, KeyError, TypeError, OverflowError):
            continue
        if now - ts <= WINDOW_SEC:
            recent.append(entry)
    if recent:
        last = recent[-1]
        print(f"[loop-gate] ⚠ 過去 24h 有 {len(recent)} 次 hook 失敗"
              f"（最近：{last['hook']} — {last['error'][:120]}），詳見 {path}。"
              f"請主動告知使用者。")
    sys.exit(0)


if __name__ == "__main__":
    hook_health.guard("report_health", main)
