"""Quota Pacer 節奏裁決 CLI：skill 每做完一塊工作就叫它。

印一行： <VERDICT> <trigger> | 5h X% weekly Y% [⚠STALE]
VERDICT ∈ CONTINUE / WINDDOWN / HARDSTOP / EMERGENCY
"""
import sys

import pace_core as pc

def main():
    active_path = sys.argv[1] if len(sys.argv) > 1 else pc.ACTIVE_FILE
    try:
        usage = pc.load_usage()
    except (OSError, ValueError):
        print("HARDSTOP state-missing | 讀不到用量，保守停手")
        return
    try:
        active = pc.load_active(active_path)
    except (OSError, ValueError):
        print("CONTINUE none | pacer 未啟用（無 active.json）")
        return

    verdict, trigger = pc.evaluate(usage, active)
    age = int(usage.get("_age", 0))
    stale = " ⚠STALE({}s)".format(age) if age > pc.STALE else ""
    h5 = usage.get("five_hour", {}).get("pct")
    w = usage.get("seven_day", {}).get("pct")
    print(f"{verdict} {trigger} | 5h {h5}% weekly {w}%{stale}")

if __name__ == "__main__":
    main()
