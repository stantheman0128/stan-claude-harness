"""全機規則：一條停手條件管這台機器上所有 session，由 hook 強制。

session 有沒有載入 skill 都會被擋，所以適合「睡前交代一句，所有 session 到點都停」。

用法：
  py global_pace.py --until 05:00              到早上 5 點、或 weekly 快用完、或 weekly 重置，先到的就停
  py global_pace.py                            沒有時間，只管 weekly 快用完和重置
  py global_pace.py --until 05:00 --cap 80     weekly 的上限改成 80%
  py global_pace.py --until 05:00 --budget 10  從現在起最多再用 10 個百分點
  py global_pace.py --until 05:00 --time-only  只看時間，不看用量
  py global_pace.py --status                   看現在有沒有規則、到線了沒
  py global_pace.py --clear                    解除。在 session 裡跑會被 hook 擋，除非 Stan 在那個 session 親口豁免；
                                               Stan 自己在 PowerShell 跑不受限

--until 接受 05:00、5（下一個這個時刻），或 2026-11-24T05:00。

exit code：0 = 完成；2 = 參數不對；3 = 已經有規則，session 不能解除或改鬆；4 = 用量讀不到，沒設規則
"""
import os
import sys
import time

import pace_core as pc

VALUED = ("--until", "--cap", "--budget")
BARE = ("--time-only", "--status", "--clear")

ONLY_STAN = ("全機規則只有 Stan 本人能解除或放寬：他要在這個 session 親口說「豁免」「bypass」"
             "「繞過用量限制」「解除全機規則」這類的話，或自己在 PowerShell 跑這支腳本。"
             "你不能替他決定。要把規則改得更嚴（更早的時間、更低的上限）可以直接設。")

def guard(new=None):
    """已經有規則時，session 不能解除它、不能把它改鬆。回 None 表示可以做，否則回擋下的原因。

    這個檢查放在腳本裡而不是 hook 裡：hook 靠比對指令文字認人，路徑多一個 ./ 就認不出來。
    new 是要寫進去的新規則；None 代表要解除。
    """
    sid = pc.env_sid()
    if not sid or pc.bypassed(sid):
        return None  # Stan 自己在終端機跑，或他在這個 session 豁免過
    old = pc.load_global()
    if old is None:
        return None
    if new is None:
        return "現在有全機規則（%s）。" % pc.describe_global(old)
    if isinstance(old.get("stopped"), dict) or pc.global_trip(old, None):
        return "全機規則已經到線，不能重設。"
    ou, nu = pc._num(old.get("until")), pc._num(new.get("until"))
    if ou and (not nu or nu > ou + 60):
        return "原本的規則到 %s 就停，新的比較晚或沒有時間。" % pc.fmt_clock(ou)
    if not old.get("time_only"):
        if new.get("time_only"):
            return "原本的規則有看用量，新的只看時間。"
        for label, path in pc._tracked(old):
            o = pc._top(pc._dig(old.get("ceiling") or {}, path))
            n = pc._top(pc._dig(new.get("ceiling") or {}, path))
            if n > o + 0.01:
                return "原本 %s 的上限是 %g%%，新的是 %g%%。" % (label, o, n)
    return None

def fail(msg, code=2):
    print("沒設定：%s" % msg)
    sys.exit(code)

def status():
    try:
        with open(pc.GLOBAL_FILE, encoding="utf-8") as fh:
            import json
            g = json.load(fh)
    except (OSError, ValueError):
        print("沒有全機規則")
        return
    if pc.global_expired(g):
        print("沒有全機規則（上一條已過期：%s）" % pc.describe_global(g))
        return
    print("全機規則生效中：%s" % pc.describe_global(g))
    stopped = g.get("stopped")
    if isinstance(stopped, dict):
        until = pc._num(g.get("until")) or 0
        ends = max(until, pc._num(stopped.get("t")) or 0) + pc.GLOBAL_HOLD
        print("  已到線（%s）：%s" % (pc.fmt_clock(stopped.get("t") or 0), stopped.get("text")))
        print("  所有 session 的工具都被擋，%s 自動失效；Stan 本人說豁免的 session 例外" % pc.fmt_clock(ends))
    else:
        print("  還沒到線")

def clear():
    why = guard()
    if why:
        print("沒解除：%s%s" % (why, ONLY_STAN))
        sys.exit(3)
    gone = False
    try:
        os.remove(pc.GLOBAL_FILE)
        gone = True
    except OSError:
        pass
    try:
        for name in os.listdir(pc.WRAP_DIR):
            if name.startswith("lock-"):
                continue  # 單一 session 到線的鎖不歸全機規則管，只有 Stan 豁免才解
            try:
                os.remove(os.path.join(pc.WRAP_DIR, name))
            except OSError:
                pass
    except OSError:
        pass
    print("已解除全機規則" if gone else "本來就沒有全機規則")

def main():
    args = sys.argv[1:]
    opt, bare = {}, set()
    i = 0
    while i < len(args):
        a = args[i]
        if a in BARE:
            bare.add(a)
            i += 1
        elif a in VALUED:
            if i + 1 >= len(args):
                fail("%s 後面要接值" % a)
            opt[a[2:]] = args[i + 1]
            i += 2
        else:
            fail("不認得的參數：%r" % a)
    if "--status" in bare:
        return status()
    if "--clear" in bare:
        return clear()

    now = time.time()
    g = {"set": now}
    if "until" in opt:
        ts = pc.parse_until(opt["until"], now)
        if ts is None:
            fail("--until 看不懂或已經過了：%r（寫 05:00 或 2026-11-24T05:00）" % opt["until"])
        g["until"] = ts
    nums = {}
    for k in ("cap", "budget"):
        if k in opt:
            n = pc._num(str(opt[k]).strip().rstrip("%"))
            if n is None or n <= 0:
                fail("--%s 要是正數：%r" % (k, opt[k]))
            nums[k] = n
    if len(nums) == 2:
        fail("--budget 和 --cap 擇一")

    if "--time-only" in bare:
        if "until" not in g:
            fail("--time-only 要配 --until")
        if nums:
            fail("--time-only 不能再給 --cap 或 --budget")
        g["time_only"] = True
    else:
        usage = None
        try:
            u = pc.load_usage(refresh_if_stale=True)
            if u.get("_age", 0) <= pc.GLOBAL_STALE and pc.usable(u):
                usage = u
        except (OSError, ValueError):
            pass
        if usage is None:
            fail("用量讀不到。%s。先用 get_usage 加 write_usage.py 寫入讀數再跑一次；"
                 "只要時間條件就加 --time-only" % (pc.refresh_advice() or "沒有可用的用量讀數"), 4)
        u0, resets = pc.snapshot(usage, now)
        cur = pc._num(u0.get("seven_day"))
        if cur is None:
            fail("讀數裡沒有 weekly 這一條", 4)
        ceiling = {}
        if "cap" in nums:
            if nums["cap"] <= cur:
                fail("weekly 現在已經 %g%%，不低於上限 %g%%" % (cur, nums["cap"]))
            if nums["cap"] < 100:
                ceiling["seven_day"] = nums["cap"]
        elif "budget" in nums:
            for _label, path in pc._tracked({"u0": u0}):
                top = min(100.0, pc._dig(u0, path) + nums["budget"])
                if top < 100:
                    pc._put(ceiling, path, top)
        g["u0"] = u0
        if resets:
            g["resets"] = resets
        if ceiling:
            g["ceiling"] = ceiling

    why = guard(g)
    if why:
        print("沒設定：%s%s" % (why, ONLY_STAN))
        sys.exit(3)
    pc.save_json(pc.GLOBAL_FILE, g)
    print("已設定全機規則：%s" % pc.describe_global(g))
    lines = pc.hard_lines(g)
    if lines:
        print("  用量到線後可以收尾到 %s，之後全擋" % "、".join(
            "%s %g%%" % (label, line) for label, _path, line in lines))
    print("  時間到或重置而到線的，每個 session 還能用 %d 次工具收尾，之後全擋" % pc.WRAP_CALLS)
    print("  到線後 %g 小時自動失效。要提早繼續，只有 Stan 本人在對話裡說豁免才行" % (pc.GLOBAL_HOLD / 3600))

if __name__ == "__main__":
    main()
