"""Quota Pacer PreToolUse 硬保險。每次工具呼叫前跑，兩層：

一、全機規則（global.json，global_pace.py 設的）
- 管這台機器上所有 session，session 有沒有載入 skill 都一樣。
- 到線（截止時刻到了、週用量到停手線、或週用量重置）就記下 stopped，之後數字怎麼變都維持。
- 到線後每個 session 第一次工具呼叫被擋並收到說明，接著可以收尾：
  用量到線的，放行到上限前 1 個百分點左右（預設 99%）；時間到或重置的，放行 WRAP_CALLS 次。之後全擋。
- 只有 Stan 本人能豁免：他在訊息裡親口說，bypass_prompt.py 才會替那個 session 寫記號。
  到線之後 session 自己跑 global_pace.py --clear 或重設規則，一律擋。
- hook 自己叫不到 get_usage（那是模型才有的工具）。用量超過 GLOBAL_STALE 沒更新就擋一次，
  請 session 用 get_usage 把讀數寫進來（同一 session NAG_GAP 內只擋一次）。

二、單一 session 的 pacer（sessions/<session>.json，start_pace.py 設的）
- 一個 session 一個檔，只擋開工的那個 session；開工超過 24 小時的殘留檔不理。
- 舊的共用檔 active.json 還認：有寫 session 的只管那個 session，沒寫的管所有 session。
- 只在 EMERGENCY 擋，停手那層留給 skill 寫交接。
- 擋過一次，或到線後才收工，就留下一個鎖（wrap/lock-<session>）：之後收工、讀數變舊、
  重新開工都解不開，只有 Stan 親口豁免或過了 LOCK_AGE 才解。

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
STATE_FILES = ("quota-pacer/global.json", "quota-pacer/active.json", "quota-pacer/wrap",
               "quota-pacer/sessions")

# 放行只給「整行就是一次 pacer 腳本呼叫」的指令：直譯器、這個資料夾裡的腳本、簡單參數。
# 只比對檔名的話，在任何指令後面加一句 echo eval_pace.py 就能繞過整個 hook。
_OWN_RE = re.compile(
    r'(?:py|python|python3)(?:\.exe)?[ \t]+"?([A-Za-z0-9_:./~-]+)"?'
    r'((?:[ \t]+[A-Za-z0-9_@+=:.%,/-]+)*)')

_SEP_RE = re.compile("[ \t]*(?:&&|;)[ \t]*")
_REDIR_RE = re.compile("[ \t]*(?:2>&1|>[ \t]*/dev/null)[ \t]*$")

def own_calls(cmd):
    """整行全是 pacer 腳本呼叫（可以用 && 或 ; 串好幾個）就回 [(腳本檔名, 那一段指令)]，否則回空 list。

    session 習慣把「寫讀數、檢查、收工」串成一行。每一段都要通過才算；
    只要混進一段別的指令（ls、grep、子指令、換行）就整行不算。
    """
    out = []
    for part in _SEP_RE.split((cmd or "").strip(" \t")):
        while _REDIR_RE.search(part):        # 段尾的 >/dev/null、2>&1 不影響做了什麼
            part = _REDIR_RE.sub("", part)
        m = _OWN_RE.fullmatch(part)
        if not m:
            return []
        path = m.group(1).replace("\\", "/")
        head, _, name = path.rpartition("/")
        if name not in OWN or head.lower() != SCRIPTS.lower():
            return []
        out.append((name, part))
    return out

def _status_only(part):
    """這一段 global_pace.py 呼叫是不是只有 --status 一個參數。

    只看字串裡有沒有 --status 的話，`--cap --status --clear` 會被當成查看而放行。
    """
    m = _OWN_RE.fullmatch(part)
    return bool(m) and m.group(2).split() == ["--status"]

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

LOCKED = ("這個 session 的用量上限已經到了（%s），工具鎖住了。不要再呼叫工具，也不要換別的方法繞。"
          "把做到哪、還沒做什麼、下次怎麼接寫在回覆裡，結束這一輪。"
          "只有 Stan 本人能解鎖：他要在對話裡親口說「豁免」「bypass」「繞過用量限制」這類的話。"
          "他只說「繼續」不算，這時請直接告訴他要講豁免才會放行。")

def arm_lock(sid, restarting):
    """放行 pacer 自己的腳本之前先看一眼：已經到 EMERGENCY 就先把鎖寫下去。

    不然到線後下一個呼叫剛好是 start_pace.py（重新開工把上限蓋掉）的話，鎖永遠不會寫。
    正要重新開工的（restarting）到 HARDSTOP 就鎖：該停手時重新開工等於自己再給一份預算。
    讀數多舊都拿來看，跟 end_pace.py 一樣：用量只會往上。
    """
    if not sid or pc.locked(sid) is not None:
        return
    try:
        usage = pc.load_usage()
    except (OSError, ValueError):
        usage = None
    need = pc.RANK["HARDSTOP" if restarting else "EMERGENCY"]
    for _path, active in pc.find_active(sid):
        verdict, trigger = pc.evaluate(usage, active)
        if pc.RANK[verdict] >= need:
            pc.lock(sid, trigger)
            return

def session_gate(sid):
    why = pc.locked(sid)
    if why is not None:
        block(LOCKED % (why or "已收工"))
    # 這個 session 自己的設定檔，加上管得到它的舊共用檔。
    # 別的 session 開的、開工超過一天的殘留檔，find_active 已經濾掉。
    found = pc.find_active(sid, all_if_unknown=True)
    if not found:
        return

    usage = None
    try:
        u = pc.load_usage()
        if u.get("_age", 0) <= pc.STALE:
            usage = u  # 過舊就當讀不到，時間 guard 仍生效
    except (OSError, ValueError):
        usage = None

    for _path, active in found:
        verdict, trigger = pc.evaluate(usage, active)
        if verdict == "EMERGENCY":
            pc.lock(sid, trigger)
            block("EMERGENCY：%s 死線已到，停止一切工具呼叫，立刻結束本輪。這個 session 的工具已鎖住，"
                  "跑 end_pace.py 也不會解開，只有 Stan 本人說豁免才放行。" % trigger)

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
    own = own_calls(cmd) if tool in ("Bash", "PowerShell") else []

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

    # 有限制生效時，不准直接動 pacer 的狀態檔（刪規則、自己寫豁免記號）。
    # 這只擋得住直接寫出路徑的做法，是減速丘不是保險箱：session 跟 Stan 是同一個帳號。
    if tool in ("Bash", "PowerShell", "Write", "Edit", "NotebookEdit") and not own and isinstance(ti, dict):
        blob = json.dumps(ti, ensure_ascii=False).replace("\\\\", "/").lower()
        # 看的是「機器上有沒有任何限制」，不是「這個 session 有沒有」：
        # 不然沒開 pacer 的 session 可以去刪別的 session 的設定檔
        # 完整路徑之外，也認「提到 quota-pacer 又提到狀態檔名」的寫法（cd 進去再刪、多打一個斜線）
        rest = blob.replace("local-plugins/quota-pacer", "")  # plugin 原始碼不是狀態檔
        touches = any(x in blob for x in STATE_FILES) or ("quota-pacer" in rest and any(
            x in rest for x in ("wrap/", "/wrap", "lock-", "bypass-", "sessions/", "/sessions",
                                "global.json", "active.json")))
        if touches and pc.any_limit():
            block("pacer 的狀態檔不能直接改或刪。收工用 end_pace.py；" + ONLY_STAN)

    # 解除或改寫全機規則：到線之後不行，還沒到線時 --clear 也不行。只有 --status 隨時可以看。
    if any(n == "global_pace.py" and not _status_only(part) for n, part in own):
        g = pc.load_global()
        if g is not None and not isinstance(g.get("stopped"), dict):
            pc.global_trip(g, read_usage_file())  # 截止時間剛過、還沒人記下到線的空檔
            g = pc.load_global()
        if g is not None and (isinstance(g.get("stopped"), dict) or any(
                n == "global_pace.py" and "--clear" in part for n, part in own)):
            block("全機" + ONLY_STAN)

    # pacer 自己的腳本與讀用量的工具永遠放行，不然到線之後連收工、補讀數都做不了
    if own or tool.endswith("get_usage") or tool == "ToolSearch":
        if own:
            arm_lock(sid, any(n == "start_pace.py" for n, _part in own))
        sys.exit(0)

    g = pc.load_global()
    if g is not None:
        global_gate(g, sid)
    session_gate(sid)
    sys.exit(0)

if __name__ == "__main__":
    main()
