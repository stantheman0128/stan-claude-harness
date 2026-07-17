"""Quota Pacer PreToolUse 硬保險（最後一層）。

只有當 pacer session 啟用（active.json 存在）且用量已燒穿到 EMERGENCY 層
（連寫交接的 buffer 都快沒了）時，才擋新工具呼叫。正常的 hard-stop 收尾寫交接
不在此擋，交由 skill 處理，否則會把 Write 一起擋掉。

fail-open：讀不到用量、資料過舊、或 pacer 未啟用時一律放行，不憑舊數字硬卡。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import pace_core as pc  # noqa: E402

def main():
    try:
        json.load(sys.stdin)
    except ValueError:
        pass

    if not os.path.exists(pc.ACTIVE_FILE):
        sys.exit(0)  # pacer 未啟用

    try:
        usage = pc.load_usage()
        active = pc.load_active()
    except (OSError, ValueError):
        sys.exit(0)  # 讀不到 → fail-open

    if usage.get("_age", 0) > pc.STALE:
        sys.exit(0)  # 資料過舊 → 不憑舊數字硬擋

    verdict, trigger = pc.evaluate(usage, active)
    if verdict == "EMERGENCY":
        print(f"[quota-pacer] EMERGENCY：{trigger} 額度已見底，連收尾 buffer 都快耗盡。"
              f"停止一切工具呼叫，立刻結束本輪。", file=sys.stderr)
        sys.exit(2)  # 擋這次工具呼叫
    sys.exit(0)

if __name__ == "__main__":
    main()
