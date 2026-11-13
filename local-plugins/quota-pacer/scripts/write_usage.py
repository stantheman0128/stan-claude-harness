"""把模型從桌面 App 的 get_usage 工具讀到的用量寫進 usage-state.json。

get_usage 走 App 自己的登入，不受 ~/.claude/.credentials.json 的 token 過期影響，
但只有模型叫得到，所以由 skill 叫完工具後把數字交給這支腳本。

用法（百分比是「已用」；@後面的重置時間可省，接受 ISO 8601 或 epoch 秒）：
  py write_usage.py --weekly 47@2026-11-13T21:00:00+00:00 --five-hour 12 --scoped fable=49
  沒有的那條就不要給（例如目前沒有 5h 視窗就省略 --five-hour）。

exit code：0 = 已寫入；2 = 參數不對，沒寫檔
"""
import json
import os
import sys

import pace_core as pc

def parse(val):
    """'47@2026-11-13T21:00:00+00:00' → (47, epoch 或 None)。壞值 raise ValueError。"""
    pct_s, _, reset_s = val.partition("@")
    pct = pc._num(pct_s.strip().rstrip("%"))
    if pct is None or not (0 <= pct <= 200):
        raise ValueError("百分比不是 0 到 200 的數字：%r" % val)
    reset = None
    reset_s = reset_s.strip()
    if reset_s:
        n = pc._num(reset_s)
        reset = int(n) if n else pc._iso_to_epoch(reset_s)
        if reset is None:
            raise ValueError("重置時間看不懂：%r" % reset_s)
    return {"pct": pc._pct(pct), "resets_at": reset}

def main():
    args = sys.argv[1:]
    import time
    out = {"ts": time.time(), "source": "app",
           "five_hour": {"pct": None, "resets_at": None},
           "seven_day": {"pct": None, "resets_at": None}}
    scoped = {}
    try:
        if len(args) % 2:
            raise ValueError("參數要成對")
        for flag, val in zip(args[0::2], args[1::2]):
            if flag == "--five-hour":
                out["five_hour"] = parse(val)
            elif flag == "--weekly":
                out["seven_day"] = parse(val)
            elif flag == "--scoped":
                name, sep, rest = val.partition("=")
                name = name.strip().lower().replace(" ", "-")
                if not sep or not name:
                    raise ValueError("--scoped 要寫成 名稱=百分比：%r" % val)
                scoped[name] = parse(rest)
            else:
                raise ValueError("不認得的參數：%r" % flag)
        if not pc.usable(out):
            raise ValueError("--five-hour 和 --weekly 至少要給一個")
    except ValueError as e:
        print("沒寫入：%s" % e)
        sys.exit(2)
    if scoped:
        out["scoped"] = scoped

    tmp = pc.USAGE_STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    os.replace(tmp, pc.USAGE_STATE)
    print("已寫入（來源 app）：" + json.dumps(
        {"five_hour": out["five_hour"]["pct"], "seven_day": out["seven_day"]["pct"],
         "scoped": {k: v["pct"] for k, v in scoped.items()}}, ensure_ascii=False))

if __name__ == "__main__":
    main()
