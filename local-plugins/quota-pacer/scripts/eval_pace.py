"""Quota Pacer 節奏裁決 CLI：skill 每做完一塊工作就叫它。

印一行： <VERDICT> <trigger> | [elapsed Xm/Nm] [5h X% weekly Y%] [⚠用量...]
VERDICT ∈ CONTINUE / WINDDOWN / HARDSTOP / EMERGENCY
時間 guard 只靠牆鐘，用量讀不到不影響它。
有全機規則（global_pace.py 設的）時一併檢查；沒開單一 session 的 pacer 也會看它。
"""
import sys

import pace_core as pc

def main():
    active_path = sys.argv[1] if len(sys.argv) > 1 else pc.ACTIVE_FILE
    g = pc.load_global()
    try:
        active = pc.load_active(active_path)
    except (OSError, ValueError):
        active = None
    if active is None and g is None:
        print("CONTINUE none | pacer 未啟用（無 active.json，也沒有全機規則）")
        return
    solo = active is not None
    if active is None:
        active = {}

    usage = None
    note = ""
    try:
        u = pc.load_usage(refresh_if_stale=True)
        # u0 有 scoped 基準但檔案沒 scoped 資料（statusline 蓋檔）→ 補刷一次（吃冷卻）
        if ((active.get("u0") or {}).get("scoped")
                or ((g or {}).get("u0") or {}).get("scoped")) and not u.get("scoped"):
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

    verdict, trigger = pc.evaluate(usage, active) if solo else ("CONTINUE", "none")

    minutes = pc._num(active.get("minutes"))
    # 沒有任何有效 guard（用量讀不到且沒設時間）→ 保守停手，別盲跑
    if solo and usage is None and not minutes:
        verdict, trigger = "HARDSTOP", "no-guard"

    if solo:
        # 重置一旦看到就記下來：之後用量再爬高也不會被當成還在同一週
        r = None if active.get("reset") else pc.weekly_reset(usage, active)
        changed = False
        if r:
            active["reset"] = {"limit": r[0], "was": r[1], "t": pc.time.time()}
            changed = True
        elif usage is not None and not active.get("reset"):
            changed = pc.bump_peak(usage, active)
        if changed:
            try:
                pc.save_json(active_path, active)
            except OSError:
                pass
        if trigger == "reset":
            was = (active.get("reset") or {}).get("was")
            note += " ⚠weekly 已經重置{}，新一週的額度不算在這次任務裡，收工".format(
                "" if was is None else "（重置前用到 {:g}%）".format(was))

    if g is not None:
        stopped = pc.global_trip(g, usage)
        if stopped:
            if pc.RANK["HARDSTOP"] > pc.RANK[verdict]:
                verdict, trigger = "HARDSTOP", "global"
            note += " ⚠全機規則到線：{}".format(stopped.get("text"))
        else:
            note += " 全機規則：{}".format(pc.describe_global(g))

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
