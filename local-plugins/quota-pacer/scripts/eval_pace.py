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
        u = pc.load_usage(refresh_if_stale=True)
        # u0 有 scoped 基準但檔案沒 scoped 資料（statusline 蓋檔）→ 補刷一次（吃冷卻）
        if (active.get("u0") or {}).get("scoped") and not u.get("scoped"):
            u = pc.refresh_usage() or u
        if u.get("_age", 0) > pc.STALE:
            note = " ⚠用量STALE({}s)：{}".format(
                int(u["_age"]), pc.refresh_advice() or "沒重拉")
        elif not pc.usable(u):
            note = " ⚠用量檔沒有任何數字：{}".format(pc.refresh_advice() or "沒重拉")
        else:
            usage = u
    except (OSError, ValueError):
        note = " ⚠用量讀不到：{}".format(pc.refresh_advice() or "沒有 usage-state.json")

    verdict, trigger = pc.evaluate(usage, active)

    minutes = pc._num(active.get("minutes"))
    # 沒有任何有效 guard（用量讀不到且沒設時間）→ 保守停手，別盲跑
    if usage is None and not minutes:
        verdict, trigger = "HARDSTOP", "no-guard"

    parts = []
    if minutes and active.get("started"):
        parts.append("elapsed {:.0f}m/{:.0f}m".format(
            pc.elapsed_min(active["started"]), minutes))
    if usage is not None:
        def _p(key):
            v = usage.get(key, {}).get("pct")
            return "n/a" if v is None else "{}%".format(v)
        seg = "5h {} weekly {}".format(_p("five_hour"), _p("seven_day"))
        for name, blk in (usage.get("scoped") or {}).items():
            seg += " {} {}%".format(name, blk.get("pct"))
        parts.append(seg)
        # 開工時記了基準、現在卻讀不到的 per-model 限制：那條等於沒人看，要講出來
        lost = [n for n in ((active.get("u0") or {}).get("scoped") or {})
                if (usage.get("scoped") or {}).get(n, {}).get("pct") is None]
        if lost:
            note += " ⚠沒讀到 {} 的用量，這條上限這次沒檢查（write_usage 的 --scoped 名稱要跟開工時一樣）".format(
                "、".join(lost))

    print(f"{verdict} {trigger} | {' '.join(parts)}{note}".rstrip())

if __name__ == "__main__":
    main()
