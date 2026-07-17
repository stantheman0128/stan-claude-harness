"""Quota Pacer 節奏裁決 CLI：skill 每做完一塊工作就叫它。

印一行： <VERDICT> <trigger> | [elapsed Xm/Nm] [5h X% weekly Y%] [⚠用量...]
VERDICT ∈ CONTINUE / WINDDOWN / HARDSTOP / EMERGENCY
時間 guard 只靠牆鐘，用量讀不到不影響它。
"""
import sys

import pace_core as pc

def main():
    active_path = sys.argv[1] if len(sys.argv) > 1 else pc.ACTIVE_FILE
    try:
        active = pc.load_active(active_path)
    except (OSError, ValueError):
        print("CONTINUE none | pacer 未啟用（無 active.json）")
        return

    usage = None
    note = ""
    try:
        u = pc.load_usage()
        if u.get("_age", 0) > pc.STALE:
            note = " ⚠用量STALE({}s)".format(int(u["_age"]))
        else:
            usage = u
    except (OSError, ValueError):
        note = " ⚠用量讀不到"

    verdict, trigger = pc.evaluate(usage, active)

    minutes = active.get("minutes")
    # 沒有任何有效 guard（用量讀不到且沒設時間）→ 保守停手，別盲跑
    if usage is None and not minutes:
        verdict, trigger = "HARDSTOP", "no-guard"

    parts = []
    if minutes and active.get("started"):
        parts.append("elapsed {:.0f}m/{:.0f}m".format(
            pc.elapsed_min(active["started"]), float(minutes)))
    if usage is not None:
        h5 = usage.get("five_hour", {}).get("pct")
        w = usage.get("seven_day", {}).get("pct")
        parts.append("5h {}% weekly {}%".format(h5, w))

    print(f"{verdict} {trigger} | {' '.join(parts)}{note}".rstrip())

if __name__ == "__main__":
    main()
