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
CRED_FILE = os.environ.get("QP_CRED_FILE") or os.path.join(
    os.path.expanduser("~"), ".claude", ".credentials.json")
USAGE_URL = os.environ.get("QP_USAGE_URL") or "https://api.anthropic.com/api/oauth/usage"
REFRESH_COOLDOWN = _f("QP_REFRESH_COOLDOWN_SEC", 60)
REFRESH_MARK = os.path.join(os.path.dirname(ACTIVE_FILE), ".refresh-attempt")
# hook 看到「要跑 start_pace.py」時把 session_id 寫在這，start_pace.py 再抄進 active.json
START_MARK = os.path.join(os.path.dirname(ACTIVE_FILE), ".starting-session")
ACTIVE_MAX_AGE = _f("QP_ACTIVE_MAX_HOURS", 24) * 3600  # 超過就當殘留檔，hook 不理
REFRESH_LOG = os.environ.get("QP_REFRESH_LOG") or os.path.join(
    os.path.dirname(ACTIVE_FILE), "refresh.log")
REFRESH_LOG_MAX = 64 * 1024  # 超過就只留後半

RANK = {"CONTINUE": 0, "WINDDOWN": 1, "HARDSTOP": 2, "EMERGENCY": 3}
LIMITS = {"5h": "five_hour", "weekly": "seven_day"}

def _read_usage_file():
    with open(USAGE_STATE, encoding="utf-8") as fh:
        d = json.load(fh)
    d["_age"] = time.time() - float(d.get("ts", 0))
    return d

def _iso_to_epoch(s):
    """ISO 8601（含時區）→ epoch 秒；壞值回 None。"""
    if not s:
        return None
    try:
        from datetime import datetime
        return int(datetime.fromisoformat(s).timestamp())
    except (TypeError, ValueError):
        return None

def _pct(v):
    n = _num(v)
    if n is None:
        return None
    return int(n) if float(n).is_integer() else round(n, 1)

class RefreshFail(Exception):
    """刷新失敗，帶可分類的 status。detail 絕不含 token 值。"""
    def __init__(self, status, **detail):
        Exception.__init__(self, status)
        self.status = status
        self.detail = detail

# 最近一次 refresh_usage() 的結果，給 CLI 印處置用：
# ok / cooldown / cred / auth / http / network / parse / empty / write / none(沒試過)
LAST_REFRESH = {"status": "none"}

def _read_cred():
    """回 (token, expires_epoch 或 None)。只讀不寫 credentials。"""
    try:
        with open(CRED_FILE, encoding="utf-8") as fh:
            cred = json.load(fh)
    except (OSError, ValueError) as e:
        raise RefreshFail("cred", reason=type(e).__name__)
    oauth = cred.get("claudeAiOauth", cred) if isinstance(cred, dict) else {}
    token = oauth.get("accessToken") or oauth.get("access_token")
    if not token:
        raise RefreshFail("cred", reason="no-token")
    exp = _num(oauth.get("expiresAt"))
    if exp and exp > 1e11:  # 毫秒 → 秒
        exp = exp / 1000.0
    return token, exp

def usable(u):
    """至少一條主限制有數字才算可用讀數（pct 全 None 的檔不能當讀數）。"""
    if not u:
        return False
    return any(_num((u.get(k) or {}).get("pct")) is not None
               for k in ("five_hour", "seven_day"))

def fetch_usage(timeout=10):
    """打官方 oauth/usage endpoint，轉成 usage-state.json 格式（含 scoped）。

    失敗一律 raise RefreshFail(status)，由 refresh_usage 記進 LAST_REFRESH。
    """
    import urllib.error
    import urllib.request  # 延遲載入：hook 路徑 import pace_core 時不揹網路模組
    token, exp = _read_cred()

    req = urllib.request.Request(USAGE_URL, headers={
        "Authorization": "Bearer " + token,
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "quota-pacer/0.3",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RefreshFail("auth", code=e.code, expires_at=exp,
                              expired=bool(exp and exp < time.time()))
        raise RefreshFail("http", code=e.code)
    except (urllib.error.URLError, OSError) as e:  # DNS／連線／逾時
        raise RefreshFail("network", reason=str(getattr(e, "reason", e))[:120])
    try:
        raw = json.loads(body)
    except ValueError:
        raise RefreshFail("parse")
    if not isinstance(raw, dict):
        raise RefreshFail("parse")

    out = {"ts": time.time(), "source": "oauth"}
    for key in ("five_hour", "seven_day"):
        blk = raw.get(key) or {}
        out[key] = {"pct": _pct(blk.get("utilization")),
                    "resets_at": _iso_to_epoch(blk.get("resets_at"))}
    scoped = {}
    for lim in raw.get("limits") or []:
        if lim.get("kind") != "weekly_scoped":
            continue
        model = ((lim.get("scope") or {}).get("model") or {})
        name = (model.get("display_name") or "scoped").strip().lower().replace(" ", "-")
        scoped[name] = {"pct": _pct(lim.get("percent")),
                        "resets_at": _iso_to_epoch(lim.get("resets_at"))}
    if scoped:
        out["scoped"] = scoped
    if not usable(out):
        raise RefreshFail("empty")  # 200 但兩條主限制都沒數字，不寫檔
    return out

def _refresh_usage(force=False):
    """拉新用量寫 USAGE_STATE。成功回 dict、失敗/冷卻中回 None，絕不覆寫壞資料。

    失敗原因記在 LAST_REFRESH（status + detail），呼叫端用 refresh_advice() 轉成處置。
    """
    global LAST_REFRESH
    if not force:
        try:
            mark = os.path.getmtime(REFRESH_MARK)
            left = REFRESH_COOLDOWN - (time.time() - mark)
            try:  # token 檔在上次嘗試之後被換過 → 免冷卻，修好就能馬上重讀
                cred_newer = os.path.getmtime(CRED_FILE) > mark
            except OSError:
                cred_newer = False
            if left > 0 and not cred_newer:
                LAST_REFRESH = {"status": "cooldown", "wait": int(left) + 1}
                return None
        except OSError:
            pass
    try:
        os.makedirs(os.path.dirname(REFRESH_MARK), exist_ok=True)
        with open(REFRESH_MARK, "w"):
            pass
    except OSError:
        pass
    try:
        data = fetch_usage()
    except RefreshFail as e:
        LAST_REFRESH = dict(e.detail, status=e.status)
        return None
    except Exception as e:  # 沒料到的錯也要留名字，不再無聲吞掉
        LAST_REFRESH = {"status": "error", "reason": type(e).__name__}
        return None
    tmp = USAGE_STATE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        os.replace(tmp, USAGE_STATE)
    except OSError as e:
        LAST_REFRESH = {"status": "write", "reason": type(e).__name__}
        return None
    LAST_REFRESH = {"status": "ok"}
    data = dict(data)
    data["_age"] = 0.0
    return data

def _log_refresh(force):
    """每次刷新嘗試記一行 JSONL（含冷卻被擋的），事後查得到當時為什麼沒拉。

    不記 token、不記回應內容。寫不進去就算了，不能讓記錄拖垮裁決。
    """
    import sys
    try:
        rec = dict(LAST_REFRESH)
        rec.update(t=time.strftime("%Y-%m-%d %H:%M:%S"), force=bool(force), pid=os.getpid(),
                   caller=os.path.basename(sys.argv[0] or "?"))
        try:
            rec["mark_age"] = round(time.time() - os.path.getmtime(REFRESH_MARK), 1)
        except OSError:
            rec["mark_age"] = None
        os.makedirs(os.path.dirname(REFRESH_LOG), exist_ok=True)
        try:
            if os.path.getsize(REFRESH_LOG) > REFRESH_LOG_MAX:
                with open(REFRESH_LOG, encoding="utf-8") as fh:
                    lines = fh.readlines()
                with open(REFRESH_LOG, "w", encoding="utf-8") as fh:
                    fh.writelines(lines[len(lines) // 2:])
        except OSError:
            pass
        with open(REFRESH_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + chr(10))
    except Exception:
        pass

def refresh_usage(force=False):
    """_refresh_usage 加紀錄。成功回 dict、失敗/冷卻中回 None，原因在 LAST_REFRESH 與 refresh.log。"""
    data = _refresh_usage(force)
    _log_refresh(force)
    return data

def _fmt_dur(sec):
    sec = int(abs(sec))
    return "%dh%02dm" % (sec // 3600, (sec % 3600) // 60)

def refresh_advice(st=None):
    """把 LAST_REFRESH 轉成一行「原因 → 處置」。ok/none 回空字串。"""
    st = st or LAST_REFRESH
    s = st.get("status")
    cli = '在一般 PowerShell（不是桌面 App）跑一次 claude -p "ok" --model claude-haiku-5-5 讓 CLI 換 token，再重跑'
    if s in ("ok", "none", None):
        return ""
    if s == "cooldown":
        return "冷卻中，上次嘗試不到 %ds 前 → 等 %ds 或加 --force 重試" % (
            int(REFRESH_COOLDOWN), st.get("wait", 0))
    if s == "auth":
        exp = st.get("expires_at")
        if st.get("expired") and exp:
            return "HTTP %s，檔裡的 access token 已過期（expiresAt %s，過了 %s）→ %s" % (
                st.get("code"), time.strftime("%m-%d %H:%M", time.localtime(exp)),
                _fmt_dur(time.time() - exp), cli)
        return ("HTTP %s，但檔裡的 token 照 expiresAt 還沒過期 → 可能被輪替或撤銷；先%s，"
                "還是 %s 就跑 claude auth status 看登入" % (st.get("code"), cli, st.get("code")))
    if s == "cred":
        return "讀不到 OAuth token（%s：%s）→ 確認檔案存在，或跑 claude 登入" % (
            CRED_FILE, st.get("reason"))
    if s == "network":
        return "網路錯誤（%s）→ 檢查連線後重試，token 沒問題" % st.get("reason")
    if s == "http":
        return "endpoint 回 HTTP %s → 不是 token 問題，稍後重試" % st.get("code")
    if s in ("parse", "empty"):
        return "endpoint 回 200 但沒有可用數字（%s）→ 稍後重試；持續發生代表回應格式變了" % s
    if s == "write":
        return "拉到了但寫不進 %s（%s）" % (USAGE_STATE, st.get("reason"))
    return "刷新失敗（%s %s）" % (s, st.get("reason", ""))

def load_usage(refresh_if_stale=False, force=False):
    """讀 usage state。refresh_if_stale=True 時，檔案缺/過舊/沒有可用數字就先自拉一次。

    hook 路徑請維持預設 False（PreToolUse 每次工具呼叫都跑，不能揹網路延遲）。
    刷新失敗時回舊檔（_age 照實），原因看 LAST_REFRESH；呼叫端要自己用 usable() 把關。
    """
    if not refresh_if_stale:
        return _read_usage_file()
    try:
        d = _read_usage_file()
    except (OSError, ValueError):
        d = None
    if force or d is None or d.get("_age", 0) > STALE or not usable(d):
        fresh = refresh_usage(force=force)
        if fresh is not None:
            return fresh
    if d is None:
        return _read_usage_file()  # 沒舊檔又刷不到 → 照舊 raise 給呼叫端
    return d

def load_active(path=ACTIVE_FILE):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

def _top(ceil):
    """這條限制的上限：預設 100（平台的牆），active.json 的 ceiling 可以設得更低。"""
    c = _num(ceil)
    return 100.0 if c is None else max(0.0, min(100.0, c))

def thresholds(u0, ceil=None):
    """回 (wind-down, hard-stop, emergency) 三條線，單位是「離上限還剩幾個百分點」。

    上限是自訂預算時，FLOOR/GAP/EMERGENCY 這些固定 pp 值跟著預算縮小，
    不然 5pp 的預算會被 3pp 的 FLOOR 吃掉大半。
    """
    top = _top(ceil)
    avail = max(0.0, top - u0)
    if top >= 100.0:
        floor, gap, emg = FLOOR, GAP, EMERGENCY
    else:
        floor, gap, emg = min(FLOOR, 0.2 * avail), min(GAP, 0.2 * avail), min(EMERGENCY, 0.1 * avail)
    hs = max(HARD * avail, floor)
    wd = max(SOFT * avail, hs + gap)
    return wd, hs, emg

def eval_limit(cur, u0, ceil=None):
    if cur is None or u0 is None:
        return "CONTINUE"
    rem = _top(ceil) - cur
    wd, hs, emg = thresholds(u0, ceil)
    if rem <= emg:
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
        ceiling = active.get("ceiling") or {}  # 自訂上限（預算模式），沒有就是 100
        names = ["weekly"] if mode == "5h-override" else ["5h", "weekly"]
        for name in names:
            key = LIMITS[name]
            cur = usage.get(key, {}).get("pct")
            v = eval_limit(cur, u0.get(key), ceiling.get(key))
            if RANK[v] > RANK[verdict]:
                verdict, trigger = v, name

        # scoped weekly（per-model，如 fable）：有基準的每條都套同一公式。
        # 5h-override 不豁免——它們本質是 weekly。
        u0_scoped = u0.get("scoped") or {}
        usage_scoped = usage.get("scoped") or {}
        ceil_scoped = ceiling.get("scoped") or {}
        for name, base in u0_scoped.items():
            cur = (usage_scoped.get(name) or {}).get("pct")
            v = eval_limit(cur, _num(base), ceil_scoped.get(name))
            if RANK[v] > RANK[verdict]:
                verdict, trigger = v, "weekly[%s]" % name

    return verdict, trigger
