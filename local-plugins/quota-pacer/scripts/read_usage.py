"""Quota Pacer 用量讀取器：印當前 5h/weekly/scoped 用量與資料新鮮度。

檔案缺、過舊或沒有可用數字會先自拉官方 oauth/usage endpoint（60s 冷卻）。
拉不到時第一行印「UNUSABLE 原因 → 處置」，exit 4；舊資料只當參考附在後面。

用法：
  py read_usage.py           人看的一行
  py read_usage.py --json    給 skill 記基準用的 JSON（看 usable 欄位）
  py read_usage.py --force   跳過冷卻立刻重拉

exit code：0 = 新鮮可用；3 = 沒有任何檔案；4 = 讀數不可用（過舊或全是 None）
"""
import json
import sys
import time

import pace_core as pc

def fmt_reset(resets_at, now):
    if not resets_at:
        return "?"
    d = int(resets_at) - int(now)
    if d <= 0:
        return "now"
    return f"{d // 3600}h{(d % 3600) // 60:02d}m"

def fmt_limit(label, blk, now):
    pct = (blk or {}).get("pct")
    if pct is None:
        return f"{label} n/a"  # endpoint 沒回這條（例如目前沒有 5h 視窗）
    return f"{label} {pct}% (reset {fmt_reset((blk or {}).get('resets_at'), now)})"

def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    advice = ""
    try:
        u = pc.load_usage(refresh_if_stale=True, force="--force" in args)
    except (OSError, ValueError):
        u = None
    advice = pc.refresh_advice()

    if u is None:
        why = advice or "usage-state.json 讀不到"
        if as_json:
            print(json.dumps({"usable": False, "refresh": pc.LAST_REFRESH["status"],
                              "advice": why}, ensure_ascii=False))
        else:
            print(f"UNUSABLE  {why}")
        sys.exit(3)

    h5 = u.get("five_hour", {}).get("pct")
    w = u.get("seven_day", {}).get("pct")
    scoped = {k: v.get("pct") for k, v in (u.get("scoped") or {}).items()}
    age = int(u.get("_age", 0))
    stale = age > pc.STALE
    ok = pc.usable(u) and not stale

    if as_json:
        print(json.dumps({"five_hour": h5, "seven_day": w, "scoped": scoped,
                          "age": age, "stale": stale, "usable": ok,
                          "refresh": pc.LAST_REFRESH["status"], "advice": advice},
                         ensure_ascii=False))
        sys.exit(0 if ok else 4)

    now = time.time()
    sc = "".join(f"  |  {k} {v}%" for k, v in scoped.items() if v is not None)
    line = (f"{fmt_limit('5h', u.get('five_hour'), now)}  |  "
            f"{fmt_limit('weekly', u.get('seven_day'), now)}{sc}  |  {age}s ago")
    if ok:
        print(line)
        return
    why = advice or ("檔案裡沒有任何用量數字" if not pc.usable(u) else "資料過舊且沒重拉")
    print(f"UNUSABLE  {why}")
    if pc.usable(u):
        print(f"（舊資料，別拿來記基準）{line}")
    sys.exit(4)

if __name__ == "__main__":
    main()
