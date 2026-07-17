"""Quota Pacer 用量讀取器：印當前 5h/weekly 用量與資料新鮮度。

用法：
  py read_usage.py          人看的一行
  py read_usage.py --json   給 skill 記基準用的 JSON
"""
import json
import sys

import pace_core as pc

def fmt_reset(resets_at, now):
    if not resets_at:
        return "?"
    d = int(resets_at) - int(now)
    if d <= 0:
        return "now"
    return f"{d // 3600}h{(d % 3600) // 60:02d}m"

def main():
    try:
        u = pc.load_usage()
    except (OSError, ValueError):
        print(f"MISSING\tusage-state.json 讀不到（{pc.USAGE_STATE}）。"
              f"在互動式 CLI 敲一下讓 statusline 重繪再試。", file=sys.stderr)
        sys.exit(3)

    h5 = u.get("five_hour", {}).get("pct")
    w = u.get("seven_day", {}).get("pct")
    age = int(u.get("_age", 0))
    stale = age > pc.STALE

    if "--json" in sys.argv[1:]:
        print(json.dumps({"five_hour": h5, "seven_day": w, "age": age, "stale": stale}))
        return

    import time
    now = time.time()
    h5r = fmt_reset(u.get("five_hour", {}).get("resets_at"), now)
    wr = fmt_reset(u.get("seven_day", {}).get("resets_at"), now)
    tag = f"  ⚠STALE({age}s)" if stale else ""
    print(f"5h {h5}% (reset {h5r})  |  weekly {w}% (reset {wr})  |  {age}s ago{tag}")

if __name__ == "__main__":
    main()
