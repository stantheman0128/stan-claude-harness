"""Quota Pacer PreToolUse 硬保險（最後一層）。

active.json 存在時：
- 時間 guard 一律評（只靠牆鐘）：超過 minutes 死線 → EMERGENCY → 擋。
- 用量 guard 只在用量可讀且不過舊時才評：燒穿到 EMERGENCY 層 → 擋。
刻意不擋在 hard-stop（那層留給 skill 寫交接，否則會把 Write 一起擋掉）。
只擋開工的那個 session（active.json 的 session）；開工超過 24 小時的殘留檔不理。
pacer 自己的腳本（含 end_pace.py）和 get_usage 永遠放行，到線之後才收得了工。
讀不到用量不影響時間 guard；沒有任一有效 guard 時放行（交給 skill 判斷）。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import pace_core as pc  # noqa: E402

OWN = ("start_pace.py", "eval_pace.py", "write_usage.py", "read_usage.py", "end_pace.py")

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
    own = tool in ("Bash", "PowerShell") and any(n in cmd for n in OWN)

    # 這個 session 正要開工：先記下是誰，start_pace.py 會抄進 active.json
    if own and "start_pace.py" in cmd and sid:
        try:
            os.makedirs(os.path.dirname(pc.START_MARK), exist_ok=True)
            with open(pc.START_MARK, "w", encoding="utf-8") as fh:
                fh.write(sid)
        except OSError:
            pass

    if not os.path.exists(pc.ACTIVE_FILE):
        sys.exit(0)  # pacer 未啟用

    try:
        active = pc.load_active()
    except (OSError, ValueError):
        sys.exit(0)
    if not isinstance(active, dict):
        sys.exit(0)

    # 別的 session 開的 → 不關這個 session 的事
    if active.get("session") and sid and active["session"] != sid:
        sys.exit(0)
    # 開工超過一天還在 → 當成沒收工的殘留檔
    started = pc._num(active.get("started"))
    if started and time.time() - started > pc.ACTIVE_MAX_AGE:
        sys.exit(0)
    # pacer 自己的腳本與讀用量的工具永遠放行，不然到線之後連收工都做不了
    if own or tool.endswith("get_usage") or tool == "ToolSearch":
        sys.exit(0)

    usage = None
    try:
        u = pc.load_usage()
        if u.get("_age", 0) <= pc.STALE:
            usage = u  # 過舊就當讀不到，時間 guard 仍生效
    except (OSError, ValueError):
        usage = None

    verdict, trigger = pc.evaluate(usage, active)
    if verdict == "EMERGENCY":
        print(f"[quota-pacer] EMERGENCY：{trigger} 死線已到，停止一切工具呼叫，立刻結束本輪。",
              file=sys.stderr)
        sys.exit(2)  # 擋這次工具呼叫
    sys.exit(0)

if __name__ == "__main__":
    main()
