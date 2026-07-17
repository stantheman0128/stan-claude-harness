"""Quota Pacer PreToolUse 硬保險（最後一層）。

active.json 存在時：
- 時間 guard 一律評（只靠牆鐘）：超過 minutes 死線 → EMERGENCY → 擋。
- 用量 guard 只在用量可讀且不過舊時才評：燒穿到 EMERGENCY 層 → 擋。
刻意不擋在 hard-stop（那層留給 skill 寫交接，否則會把 Write 一起擋掉）。
讀不到用量不影響時間 guard；沒有任一有效 guard 時放行（交給 skill 判斷）。
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
        active = pc.load_active()
    except (OSError, ValueError):
        sys.exit(0)

    usage = None
    try:
        u = pc.load_usage()
        if u.get("_age", 0) <= pc.STALE:
            usage = u  # 過舊就當讀不到，時間 guard 仍生效
    except (OSError, ValueError):
        usage = None

    verdict, trigger = pc.evaluate(usage, active)
    if verdict == "EMERGENCY":
        print(f"[quota-pacer] EMERGENCY：{trigger} 死線已到，停止一切工具呼叫，立刻結束本輪。",
              file=sys.stderr)
        sys.exit(2)  # 擋這次工具呼叫
    sys.exit(0)

if __name__ == "__main__":
    main()
