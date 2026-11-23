"""Quota Pacer UserPromptSubmit：Stan 本人在訊息裡說豁免，這個 session 才不受用量限制擋。

只有使用者送出的訊息會觸發這支 hook，模型自己叫不到，所以拿它當「本人親口說」的憑據。
看到豁免的說法就在 wrap/ 寫一個 bypass-<session> 記號，工具 hook 看到記號就放行這個 session。
只放行講這句話的 session，其他 session 照舊。沒有任何生效中的限制時不寫記號。

背景任務回報、subagent 交回、斜線指令展開的內文也會走這支 hook，那些不是 Stan 講的，一律跳過。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import pace_core as pc  # noqa: E402

# 不是 Stan 親手打的訊息
NOT_HUMAN = ("<task-notification>", "<command-name>", "<command-message>", "[Subagent hand-back]",
             "<agent-message>", "<side-sessions-event>", "<ci-monitor-event>", "<system-reminder>")
# 強的說法：出現在用量這類詞附近就算。
VERB = "bypass|豁免|繞過|無視"
OBJ = "用量|額度|pacer|quota|weekly|usage|全機規則|停手規則|停手|限額"
# 弱的說法（解除、取消、忽略、不管）平常講話太常用，「額度快沒了，取消剩下的工作」不是豁免。
# 只有緊接著講到限制、上限、規則本身才算：「不用管用量限制」「解除全機規則」「取消用量上限」。
WEAK = re.compile("(?:解除|取消|忽略|不用管|不必管|不管)(?:這個|那個|我的|這條|那條)?.{0,6}?"
                  "(?:限制|上限|停手規則|全機規則|限額)", re.I | re.S)
# 說法後面緊接著否定或問句（「…？不行，停」「可以繞過用量限制嗎」）也不算
AFTER_NEG = re.compile("不行|不可以|不准|不要|不能|嗎|？|\\?")
NEG = "不要|別|不准|不可以|不能|不得|勿|禁止|不可|不許|不會|沒有|沒說|不是"
NEAR = re.compile("(?:(%s).{0,12}(%s))|(?:(%s).{0,12}(%s))" % (VERB, OBJ, OBJ, VERB), re.I | re.S)
# 「限制」「上限」單獨出現太常見，只跟這幾個動詞緊鄰時才算
NEAR2 = re.compile("(?:(?:bypass|豁免|繞過|無視|不管|不用管).{0,8}(?:限制|上限))"
                   "|(?:(?:限制|上限).{0,8}(?:bypass|豁免))", re.I | re.S)
# 整則訊息幾乎只有這個詞（「bypass」「我豁免，繼續做」）才算；長訊息裡單獨一個 bypass 多半在講別的事
SHORT = re.compile("bypass|豁免", re.I)
SHORT_MAX = 14
NEG_RE = re.compile(NEG)

def negated(text, start):
    """說法前面幾個字有否定詞（「不要繞過用量限制」）就不算。"""
    return bool(NEG_RE.search(text[max(0, start - 8):start]))

def taken_back(text, end):
    return bool(AFTER_NEG.search(text[end:end + 10]))

def wants_bypass(prompt):
    text = re.sub("<pasted_content.*?</pasted_content[^>]*>", " ", prompt, flags=re.S).strip() or prompt
    for rx in (NEAR, NEAR2, WEAK):
        for m in rx.finditer(text):
            if not negated(text, m.start()) and not taken_back(text, m.end()):
                return True
    if len(text) <= SHORT_MAX:
        for m in SHORT.finditer(text):
            if not negated(text, m.start()):
                return True
    return False

def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return
    if not isinstance(data, dict):
        return
    prompt = (data.get("prompt") or "").strip()
    sid = data.get("session_id") or ""
    if not prompt or not sid or any(t in prompt for t in NOT_HUMAN):
        return
    if not pc.has_limit(sid):
        return  # 沒有東西可以豁免
    if not wants_bypass(prompt):
        return
    try:
        os.makedirs(pc.WRAP_DIR, exist_ok=True)
        with open(pc.mark_path(sid, "bypass"), "w"):
            pass
    except OSError:
        return
    pc.unlock(sid)  # 到線留下的鎖一起解掉，豁免過期後不會又被舊鎖擋
    print("[quota-pacer] Stan 本人在這則訊息豁免了用量限制：這個 session 接下來 %g 小時不受全機規則和 "
          "pacer 的擋，照他說的做。其他 session 不受影響。他如果是要解除整條全機規則，跑 "
          'py "C:/Users/stans/.claude/local-plugins/quota-pacer/scripts/global_pace.py" --clear。'
          % (pc.BYPASS_AGE / 3600))

if __name__ == "__main__":
    main()
