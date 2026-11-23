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
AFTER_NEG = re.compile("^的|不行|不可以|不准|不要|不能|收回|是不對|是錯|不對|嗎|？|\\?")
# 受詞在前的說法：「額度不用管了」「用量限制先別管」
OBJ_FIRST = re.compile("(?:用量|額度|上限|限額)(?:限制|上限)?.{0,3}?"
                       "(?:不用管|先別管|別管|不用理|不用顧|不必管)", re.S)
VERB_FIRST = re.compile("(?:不用理|別管|不用顧|不用管|不必管)(?:用量|額度)(?!怎)")
OVER = re.compile("(?:可以|准你|允許你?|讓你)超過.{0,4}?(?:上限|用量|額度|限制)", re.S)
EN = re.compile("(?:ignore|override|skip|bypass|disregard|lift)\\s+(?:it\\b|this\\b|(?:the\\s+|my\\s+)?"
                "(?:(?:usage|quota|weekly|rate)\\s+)?(?:limit|cap|quota|pacer))", re.I)
# 這幾條的否定詞可能就長在說法裡面（「不用管」「別管」），所以不查前面的否定
SELF_NEG = (OBJ_FIRST, VERB_FIRST)
NEG = ("不要|別|不准|不可以|不能|不得|勿|禁止|不可|不許|不會|沒有|沒說|不是|不想|不用|不必"
       "|取消|解除|收回|什麼是|解釋|如果|要不要|該不該|能不能|可不可以"
       "|do not|don't|dont|don’t|never|no |not |should i|shall i|can i|could i|may i|whether|what is")
NEAR = re.compile("(?:(%s).{0,12}(%s))|(?:(%s).{0,12}(%s))" % (VERB, OBJ, OBJ, VERB), re.I | re.S)
# 「限制」「上限」單獨出現太常見，只跟這幾個動詞緊鄰時才算
NEAR2 = re.compile("(?:(?:bypass|豁免|繞過|無視|不管|不用管).{0,8}(?:限制|上限))"
                   "|(?:(?:限制|上限).{0,8}(?:bypass|豁免))", re.I | re.S)
# 整則訊息幾乎只有這個詞（「bypass」「我豁免，繼續做」）才算；長訊息裡單獨一個 bypass 多半在講別的事
SHORT = re.compile("bypass|豁免", re.I)
SHORT_MAX = 20
NEG_RE = re.compile(NEG, re.I)

def negated(text, start):
    """說法前面有否定詞（「不要繞過用量限制」「don't bypass」）就不算。"""
    return bool(NEG_RE.search(text[max(0, start - 12):start]))

def verb_start(m):
    """比對到的那段裡，動詞從哪開始。受詞在前（「用量到了就停，不要繞過」）時否定詞貼在動詞前面，不在整段前面。"""
    if m.re is NEAR:
        return m.start(1) if m.group(1) else m.start(4)
    return m.start()

def taken_back(text, end):
    return bool(AFTER_NEG.search(text[end:end + 10]))

def wants_bypass(prompt):
    text = re.sub("<pasted_content.*?</pasted_content[^>]*>", " ", prompt, flags=re.S).strip() or prompt
    if re.search("[?？嗎]\\s*$", text):
        return False  # 整則是問句
    for rx in (NEAR, NEAR2, WEAK, OVER, EN):
        for m in rx.finditer(text):
            vs = verb_start(m)
            if not negated(text, vs) and not negated(text, m.start()) and not taken_back(text, m.end()):
                return True
    for rx in SELF_NEG:
        for m in rx.finditer(text):
            if not taken_back(text, m.end()) and not re.search("不要|別說|不是說", text[max(0, m.start() - 6):m.start()]):
                return True
    if len(text) <= SHORT_MAX:
        for m in SHORT.finditer(text):
            if not negated(text, m.start()) and not taken_back(text, m.end()):
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
