"""Quota Pacer 核心：讀用量、讀 active 基準、算裁決。hook 與 eval CLI 共用。

兩條 guard，先到者觸發：
- 用量 guard：每條限制 session 起點記 U0，available=100-U0，正規化門檻。
- 時間 guard：從 started 起算 elapsed 分鐘，minutes 為上限；只靠牆鐘，不碰用量資料，
  所以在讀不到 usage 的環境（SDK / 桌面 App）照樣有效。

門檻與時間盒模型見 docs/specs/2026-07-18-quota-pacer-design.md。
EMERGENCY 是給 hook 的最後保險，低於 hard-stop，確保寫交接的 buffer 不會被 hook 擋掉。
"""
import json
import os
import time

def _f(env, default):
    try:
        return float(os.environ.get(env, default))
    except (TypeError, ValueError):
        return float(default)

def _num(x):
    """安全轉數字，壞值回 None（防 active.json 被寫壞時 float() 爆例外）。"""
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

SOFT = _f("QP_SOFT_RATIO", 0.10)
HARD = _f("QP_HARD_RATIO", 0.05)
FLOOR = _f("QP_FLOOR_PP", 3)
GAP = _f("QP_NOTICE_GAP_PP", 1)
EMERGENCY = _f("QP_EMERGENCY_PP", 1)
STALE = _f("QP_STALE_SEC", 90)
GRACE_MIN = _f("QP_GRACE_MIN", 3)
NOTICE_MIN = _f("QP_NOTICE_MIN", 2)

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

def elapsed_min(started):
    n = _num(started)
    if not n or n <= 0:
        return 0.0
    return (time.time() - n) / 60.0

def eval_time(started, minutes):
    s, m = _num(started), _num(minutes)
    if not s or not m or s <= 0 or m <= 0:
        return "CONTINUE"
    e = (time.time() - s) / 60.0
    hard_at = max(0.0, m - GRACE_MIN)
    wind_at = max(0.0, hard_at - NOTICE_MIN)
    if e >= m:
        return "EMERGENCY"
    if e >= hard_at:
        return "HARDSTOP"
    if e >= wind_at:
        return "WINDDOWN"
    return "CONTINUE"

def evaluate(usage, active):
    """回 (verdict, trigger)。時間與用量兩條 guard 先到者。usage 可為 None（讀不到）。"""
    verdict, trigger = "CONTINUE", ""

    if _num(active.get("minutes")):
        v = eval_time(active.get("started"), active.get("minutes"))
        if RANK[v] > RANK[verdict]:
            verdict, trigger = v, "time"

    if usage is not None:
        mode = active.get("mode", "both")
        u0 = active.get("u0", {})
        names = ["weekly"] if mode == "5h-override" else ["5h", "weekly"]
        for name in names:
            key = LIMITS[name]
            cur = usage.get(key, {}).get("pct")
            v = eval_limit(cur, u0.get(key))
            if RANK[v] > RANK[verdict]:
                verdict, trigger = v, name

    return verdict, trigger
