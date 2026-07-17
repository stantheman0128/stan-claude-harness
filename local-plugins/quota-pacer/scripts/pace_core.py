"""Quota Pacer 核心：讀用量、讀 active 基準、算裁決。hook 與 eval CLI 共用。

門檻模型見 docs/specs/2026-07-18-quota-pacer-design.md。
每條限制在 session 起點記一次基準 U0，把當下還剩的正規化成 available=100-U0，
再取 soft/hard 比例與 FLOOR 地板。EMERGENCY 是給 hook 的最後保險，低於 hard-stop，
確保寫交接的那段 buffer 不會被 hook 擋掉。
"""
import json
import os
import time

def _f(env, default):
    try:
        return float(os.environ.get(env, default))
    except (TypeError, ValueError):
        return float(default)

SOFT = _f("QP_SOFT_RATIO", 0.10)
HARD = _f("QP_HARD_RATIO", 0.05)
FLOOR = _f("QP_FLOOR_PP", 3)
GAP = _f("QP_NOTICE_GAP_PP", 1)
EMERGENCY = _f("QP_EMERGENCY_PP", 1)
STALE = _f("QP_STALE_SEC", 90)

USAGE_STATE = os.environ.get("QP_USAGE_STATE") or os.path.join(
    os.path.expanduser("~"), ".claude", "usage-state.json")
ACTIVE_FILE = os.environ.get("QP_ACTIVE_FILE") or os.path.join(
    os.path.expanduser("~"), ".claude", "quota-pacer", "active.json")

RANK = {"CONTINUE": 0, "WINDDOWN": 1, "HARDSTOP": 2, "EMERGENCY": 3}
LIMITS = {"5h": "five_hour", "weekly": "seven_day"}

def load_usage():
    with open(USAGE_STATE, encoding="utf-8") as fh:
        d = json.load(fh)
    d["_age"] = time.time() - float(d.get("ts", 0))
    return d

def load_active(path=ACTIVE_FILE):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

def thresholds(u0):
    avail = max(0.0, 100.0 - u0)
    hs = max(HARD * avail, FLOOR)
    wd = max(SOFT * avail, hs + GAP)
    return wd, hs

def eval_limit(cur, u0):
    if cur is None or u0 is None:
        return "CONTINUE"
    rem = 100.0 - cur
    wd, hs = thresholds(u0)
    if rem <= EMERGENCY:
        return "EMERGENCY"
    if rem <= hs:
        return "HARDSTOP"
    if rem <= wd:
        return "WINDDOWN"
    return "CONTINUE"

def evaluate(usage, active):
    """回 (verdict, trigger)。先到者：取所有啟用限制中最嚴重的。"""
    mode = active.get("mode", "both")
    u0 = active.get("u0", {})
    names = ["weekly"] if mode == "5h-override" else ["5h", "weekly"]
    verdict, trigger = "CONTINUE", ""
    for name in names:
        key = LIMITS[name]
        cur = usage.get(key, {}).get("pct")
        v = eval_limit(cur, u0.get(key))
        if RANK[v] > RANK[verdict]:
            verdict, trigger = v, name
    return verdict, trigger
