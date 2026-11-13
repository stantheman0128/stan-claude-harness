"""開工：讀當前用量當基準，寫 active.json，印出會在哪裡收手。

用法：
  py start_pace.py                      只防撞到 100%
  py start_pace.py --budget 5           這次最多再用 5 個百分點（weekly 和每條 per-model weekly 各自起點 +5）
  py start_pace.py --cap 60             weekly（全部模型）到 60% 就停
  py start_pace.py --minutes 30         時間盒，可跟上面併用
  py start_pace.py --mode 5h-override   忽略 5h，只管 weekly

先用 write_usage.py 把 get_usage 的數字寫進檔，再跑這支；不然它會自己打 endpoint。

exit code：0 = 已寫 active.json；2 = 參數不對；4 = 用量讀不到又沒給 --minutes，沒寫檔
"""
import json
import os
import sys
import time

import pace_core as pc

def fail(msg, code=2):
    print("沒開工：%s" % msg)
    sys.exit(code)

def main():
    args = sys.argv[1:]
    opt = {}
    if len(args) % 2:
        fail("參數要成對")
    for flag, val in zip(args[0::2], args[1::2]):
        if flag not in ("--budget", "--cap", "--minutes", "--mode"):
            fail("不認得的參數：%r" % flag)
        opt[flag[2:]] = val
    mode = opt.get("mode", "both")
    if mode not in ("both", "5h-override"):
        fail("--mode 只能是 both 或 5h-override")
    nums = {}
    for k in ("budget", "cap", "minutes"):
        if k in opt:
            n = pc._num(str(opt[k]).strip().rstrip("%m"))
            if n is None or n <= 0:
                fail("--%s 要是正數：%r" % (k, opt[k]))
            nums[k] = n
    if "budget" in nums and "cap" in nums:
        fail("--budget 和 --cap 擇一")

    usage = None
    try:
        u = pc.load_usage(refresh_if_stale=True)
        if u.get("_age", 0) <= pc.STALE and pc.usable(u):
            usage = u
    except (OSError, ValueError):
        pass

    if usage is None:
        advice = pc.refresh_advice() or "沒有可用的用量讀數"
        if "budget" in nums or "cap" in nums:
            fail("用量讀不到，設不了用量上限。%s" % advice, 4)
        if "minutes" not in nums:
            fail("用量讀不到，也沒給 --minutes，沒有任何 guard。%s" % advice, 4)

    active = {"mode": mode, "started": time.time()}
    # 綁定 session：hook 只擋開工的這個 session，殘留檔不會卡到別的 session
    try:
        if time.time() - os.path.getmtime(pc.START_MARK) < 120:
            with open(pc.START_MARK, encoding="utf-8") as fh:
                sid = fh.read().strip()
            if sid:
                active["session"] = sid
        os.remove(pc.START_MARK)
    except OSError:
        pass
    lines = []
    if "minutes" in nums:
        active["minutes"] = nums["minutes"]
        lines.append("時間盒 %g 分：第 %g 分收手寫交接，第 %g 分硬停" % (
            nums["minutes"], max(0, nums["minutes"] - pc.GRACE_MIN), nums["minutes"]))

    if usage is not None:
        u0, ceiling = {}, {}
        rows = []  # (顯示名, 現在, 上限)
        for label, key in (("5h", "five_hour"), ("weekly", "seven_day")):
            cur = usage.get(key, {}).get("pct")
            if cur is None or (key == "five_hour" and mode == "5h-override"):
                continue
            u0[key] = cur
            top = 100.0
            if key == "seven_day":
                if "budget" in nums:
                    top = min(100.0, cur + nums["budget"])
                elif "cap" in nums:
                    top = min(100.0, nums["cap"])
                    if top <= cur:
                        fail("weekly 現在已經 %g%%，不低於上限 %g%%" % (cur, top))
                if top < 100.0:
                    ceiling[key] = top
            rows.append((label, cur, top))
        sc0, scc = {}, {}
        for name, blk in (usage.get("scoped") or {}).items():
            cur = (blk or {}).get("pct")
            if cur is None:
                continue
            sc0[name] = cur
            top = min(100.0, cur + nums["budget"]) if "budget" in nums else 100.0
            if top < 100.0:
                scc[name] = top
            rows.append(("weekly[%s]" % name, cur, top))
        if sc0:
            u0["scoped"] = sc0
        if scc:
            ceiling["scoped"] = scc
        if ("budget" in nums or "cap" in nums) and "seven_day" not in u0:
            fail("讀數裡沒有 weekly 這一條，設不了用量上限", 4)
        active["u0"] = u0
        if ceiling:
            active["ceiling"] = ceiling
        for label, cur, top in rows:
            wd, hs, emg = pc.thresholds(cur, top)
            lines.append("%s 現在 %g%%，上限 %g%%：%g%% 開始收尾，%g%% 停手寫交接，%g%% 硬擋工具" % (
                label, cur, top, top - wd, top - hs, top - emg))

    os.makedirs(os.path.dirname(pc.ACTIVE_FILE), exist_ok=True)
    tmp = pc.ACTIVE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(active, fh, ensure_ascii=False)
    os.replace(tmp, pc.ACTIVE_FILE)
    print("已開工（%s）" % pc.ACTIVE_FILE)
    for ln in lines:
        print("  " + ln)

if __name__ == "__main__":
    main()
