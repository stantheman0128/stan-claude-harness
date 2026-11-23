"""Quota Pacer PreToolUse 硬保險。每次工具呼叫前跑，兩層：

一、全機規則（global.json，global_pace.py 設的）
- 管這台機器上所有 session，session 有沒有載入 skill 都一樣。
- 到線（截止時刻到了、週用量到停手線、或週用量重置）就記下 stopped，之後數字怎麼變都維持。
- 到線後每個 session 第一次工具呼叫被擋並收到說明，接著可以收尾：
  用量到線的，放行到上限前 1 個百分點左右（預設 99%）；時間到或重置的，放行 WRAP_CALLS 次。之後全擋。
- 只有 Stan 本人能豁免：他在訊息裡親口說，bypass_prompt.py 才會替那個 session 寫記號。
  到線之後 session 自己跑 global_pace.py --clear 或重設規則，一律擋。
- 用量超過 GLOBAL_STALE 沒更新就自己去 endpoint 拉（有冷卻）；拉不到就擋一次，
  請 session 用 get_usage 把讀數寫進來（同一 session NAG_GAP 內只擋一次）。

二、單一 session 的 pacer（active.json，start_pace.py 設的）
- 只擋開工的那個 session；開工超過 24 小時的殘留檔不理。
- 只在 EMERGENCY 擋，停手那層留給 skill 寫交接。

pacer 自己的腳本、get_usage、ToolSearch 永遠放行，到線之後才收得了工、補得了讀數。
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import pace_core as pc  # noqa: E402

OWN = ("start_pace.py", "eval_pace.py", "write_usage.py", "read_usage.py", "end_pace.py",
       "global_pace.py")
SCRIPTS = "C:/Users/stans/.claude/local-plugins/quota-pacer/scripts"

# 放行只給「整行就是一次 pacer 腳本呼叫」的指令：直譯器、這個資料夾裡的腳本、簡單參數。
# 只比對檔名的話，在任何指令後面加一句 echo eval_pace.py 就能繞過整個 hook。
_OWN_RE = re.compile(
    r'(?:py|python|python3)(?:\.exe)?[ \t]+"?([A-Za-z0-9_:./~-]+)"?'
    r'((?:[ \t]+[A-Za-z0-9_@+=:.%,/-]+)*)')

def own_script(cmd):
    """整行是單一 pacer 腳本呼叫就回腳本檔名，否則回空字串。"""
    m = _OWN_RE.fullmatch((cmd or "").strip(" " + chr(9)))  # 換行也不准，整行只能有這一個呼叫
    if not m:
        return ""
    path = m.group(1).replace("\\", "/")
    head, _, name = path.rpartition("/")
    if name not in OWN or head.lower() != SCRIPTS.lower():
        return ""
    return name

def block(msg):
    print("[quota-pacer] " + msg, file=sys.stderr)
    sys.exit(2)

_mark = pc.mark_path
ONLY_STAN = ("規則只有 Stan 本人能解除或豁免：他要在對話裡親口說「豁免」「bypass」「繞過用量限制」"
             "「解除全機規則」這類的話，這個 session 才會被放行。你不能自己解除，也不要替他決定。")

def _wrap_count(sid, rule_id, bump):
    """這個 session 在這條規則到線後已經被算了幾次工具呼叫。bump=True 就加一並寫回。"""
    path = _mark(sid, "wrap")
    count = 0
    try:
        with open(path, encoding="utf-8") as fh:
            rid, _, n = fh.read().partition(" ")
        if rid == rule_id:
            count = int(n)
    except (OSError, ValueError):
        pass
    if bump:
        try:
            os.makedirs(pc.WRAP_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("%s %d" % (rule_id, count + 1))
        except OSError:
            pass
    return count

def read_usage_file():
    """讀檔裡的用量，不管多舊；沒有或沒數字回 None。"""
    try:
        u = pc.load_usage()
    except (OSError, ValueError):
        return None
    return u if pc.usable(u) else None

def global_gate(g, sid):
    need_usage = not g.get("time_only")
    usage = None
    stale = False
    if not isinstance(g.get("stopped"), dict) and need_usage:
        usage = read_usage_file()
        if usage is None or usage.get("_age", 0) > pc.GLOBAL_STALE:
            usage = pc.refresh_usage(timeout=4) or usage
        stale = usage is None or usage.get("_age", 0) > pc.GLOBAL_STALE
    stopped = pc.global_trip(g, usage)

    if not stopped:
        if stale:
            path = _mark(sid, "nag")
            try:
                recent = time.time() - os.path.getmtime(path) < pc.NAG_GAP
            except OSError:
                recent = False
            if not recent:
                try:
                    os.makedirs(pc.WRAP_DIR, exist_ok=True)
                    with open(path, "w"):
                        pass
                except OSError:
                    pass
                block("Stan 設了全機停手規則（%s），但用量讀數太舊或讀不到，沒辦法判斷到線了沒。"
                      "這次工具呼叫先擋下。請先呼叫 mcp__ccd_session_mgmt__get_usage"
                      "（列在 deferred tools 就先用 ToolSearch 載入），把每條週限額的已用百分比寫進檔："
                      'py "%s/write_usage.py" --weekly <數字> --scoped <模型英文小寫>=<數字>'
                      "，然後重試剛才的工具。沒有 get_usage 工具就直接重試。"
                      "這個提醒同一個 session %d 分鐘內只出現一次。"
                      % (pc.describe_global(g), SCRIPTS, pc.NAG_GAP // 60))
        return

    # 用量到線的：收尾放行到硬擋線（預設 99%）。讀數太舊就退回數次數，不能憑舊數字一直放行。
    hard = None
    if stopped.get("reason") == "usage":
        usage = read_usage_file()
        if usage is None or usage.get("_age", 0) > pc.GLOBAL_STALE:
            usage = pc.refresh_usage(timeout=4) or usage
        if usage is not None and usage.get("_age", 0) <= pc.GLOBAL_STALE:
            hard = pc.global_hard(usage, g)

    rule_id = "%d" % (pc._num(g.get("set")) or 0)
    used = _wrap_count(sid, rule_id, bump=True)
    if hard is None:
        room = "你還有 %d 次工具呼叫可以收尾" % pc.WRAP_CALLS
    else:
        room = "收尾可以用工具，直到%s為止" % "或".join(
            "%s 到 %g%%" % (label, line) for label, _path, line in pc.hard_lines(g))
    if used == 0 and not hard:
        block("全機停手規則到線：%s。Stan 設的規則是：%s。"
              "現在停止原本的任務，不要開始新的工作。%s"
              "（存檔、把做到一半的東西收到乾淨的狀態、寫交接），之後所有工具都會被擋。"
              "收尾後在回覆裡寫清楚：做到哪、還沒做什麼、下次怎麼接，然後結束這一輪。%s"
              % (stopped.get("text"), pc.describe_global(g), room, ONLY_STAN))
    if hard or (hard is None and used > pc.WRAP_CALLS):
        block("全機停手規則到線（%s），收尾的額度也用完了%s。不要再呼叫工具，"
              "把進度、還沒做的、下次怎麼接寫在回覆裡，結束這一輪。%s"
              % (stopped.get("text"), "：" + hard if hard else "", ONLY_STAN))

def session_gate(sid):
    try:
        active = pc.load_active()
    except (OSError, ValueError):
        return
    if not isinstance(active, dict):
        return
    # 別的 session 開的 → 不關這個 session 的事
    if active.get("session") and sid and active["session"] != sid:
        return
    # 開工超過一天還在 → 當成沒收工的殘留檔
    started = pc._num(active.get("started"))
    if started and time.time() - started > pc.ACTIVE_MAX_AGE:
        return

    usage = None
    try:
        u = pc.load_usage()
        if u.get("_age", 0) <= pc.STALE:
            usage = u  # 過舊就當讀不到，時間 guard 仍生效
    except (OSError, ValueError):
        usage = None

    verdict, trigger = pc.evaluate(usage, active)
    if verdict == "EMERGENCY":
        block("EMERGENCY：%s 死線已到，停止一切工具呼叫，立刻結束本輪。" % trigger)

def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    sid = data.get("session_id") or ""
    tool = data.get("tool_name") or ""
    ti = data.get("tool_input")
    cmd = (ti.get("command") or "") if isinstance(ti, dict) else ""
    own = own_script(cmd) if tool in ("Bash", "PowerShell") else ""

    # 這個 session 正要開工：先記下是誰，start_pace.py 會抄進 active.json。
    # 這裡只是記名字，寬鬆比對就好；放行與否看上面的 own。
    if tool in ("Bash", "PowerShell") and "start_pace.py" in cmd and sid:
        try:
            os.makedirs(os.path.dirname(pc.START_MARK), exist_ok=True)
            with open(pc.START_MARK, "w", encoding="utf-8") as fh:
                fh.write(sid)
        except OSError:
            pass

    # Stan 在這個 session 親口豁免過 → 兩層都不擋
    if pc.bypassed(sid):
        sys.exit(0)

    # 解除或改寫全機規則：到線之後不行，還沒到線時 --clear 也不行。只有 --status 隨時可以看。
    if own == "global_pace.py" and "--status" not in cmd:
        g = pc.load_global()
        if g is not None and (isinstance(g.get("stopped"), dict) or "--clear" in cmd):
            block("全機" + ONLY_STAN)

    # pacer 自己的腳本與讀用量的工具永遠放行，不然到線之後連收工、補讀數都做不了
    if own or tool.endswith("get_usage") or tool == "ToolSearch":
        sys.exit(0)

    g = pc.load_global()
    if g is not None:
        global_gate(g, sid)
    if os.path.exists(pc.ACTIVE_FILE):
        session_gate(sid)
    sys.exit(0)

if __name__ == "__main__":
    main()
