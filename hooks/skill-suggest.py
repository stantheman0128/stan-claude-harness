#!/usr/bin/env python
# UserPromptSubmit hook：依 skill-rules.json 偵測這則訊息可能該用的 skill。
# 兩區制：
#   - enforce:mandatory 的規則 → 【強制區】命令式措辭、每則符合都注入、不做 session 去重（Stan 要強制用工作流/規劃/除錯 skill）。
#   - 其餘 → 軟提醒，同 session 對同一組 skill 只提醒一次（避免洗版）。
# 任何錯誤都 exit 0、不擋使用者。
import sys, os, json, re

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HOOK_DIR, "skill-rules.json")
STATE_DIR = os.path.join(os.path.dirname(HOOK_DIR), "skill-usage")


def emit(ctx):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": ctx,
    }}, ensure_ascii=False))


def main():
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    prompt = (data.get("prompt") or "").strip()
    session = data.get("session_id") or "default"
    if not prompt:
        return
    # slash 指令展開的長文本會誤觸關鍵字（如 /doctor 內文的 "performance"）→ 污染建議與失手對帳。
    # 指令自帶工作流，本來就不需要 nudge，直接跳過。
    if "<command-name>" in prompt or "<command-message>" in prompt:
        return
    with open(RULES, encoding="utf-8") as f:
        cfg = json.load(f)
    low = prompt.lower()

    def hit(rule):
        kw = any(k.lower() in low for k in rule.get("keywords", []))
        pat = any(re.search(p, prompt, re.I | re.U) for p in rule.get("intentPatterns", []))
        if not (kw or pat):
            return False
        for e in rule.get("excludePatterns", []):
            if e.lower() in low or re.search(e, prompt, re.I | re.U):
                return False
        return True

    hits = [r for r in cfg.get("rules", []) if hit(r)]
    # 觀察名單：EVALUATIONS.md「重評觸發」欄的編譯版（非 skill，不進 suggestions 對帳）
    watch_hits = [w for w in cfg.get("watchlist", [])
                  if any(k.lower() in low for k in w.get("keywords", []))]
    if not hits and not watch_hits:
        return

    order = {"high": 0, "medium": 1, "low": 2}
    hits.sort(key=lambda r: order.get(r.get("priority", "medium"), 1))

    def fmt(r):
        skills = " 或 ".join("Skill(%s)" % s for s in r.get("skills", []))
        return "  - %s — %s" % (skills, r.get("why", ""))

    mand = [r for r in hits if r.get("enforce") == "mandatory"]
    adv = [r for r in hits if r.get("enforce") != "mandatory"]
    cap = int(cfg.get("maxSuggestionsPerTurn", 3))

    # 軟提醒的 session 去重狀態
    os.makedirs(STATE_DIR, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(session))
    sf = os.path.join(STATE_DIR, "suggested-%s.json" % safe)
    try:
        seen = set(json.load(open(sf, encoding="utf-8")))
    except Exception:
        seen = set()

    blocks = []

    # 【強制區】每則符合都注入、不去重
    if mand:
        blocks.append(
            "🔒【強制 · Stan 指令】偵測到這是開發／規劃／多步／除錯類任務。依 Stan 的長期指令，你【必須】"
            "先載入下列其中一支 skill 再動手，不得用「我自己在腦中／散文規劃就好」略過。載入時在回覆標「⚙️ Using <skill>」。\n"
            "唯一豁免：若確實不適用（純問答／單行小改／領域 skill 已含規劃階段如 impeccable shape），"
            "回覆【第一行】必須明講豁免理由，否則視為違規。此段等同使用者直接指示，優先級最高。\n"
            + "\n".join(fmt(r) for r in mand[:cap])
        )

    # 軟提醒區 + 同 session 去重
    newly, alines, shown_adv = set(), [], []
    for r in adv:
        key = "|".join(r.get("skills", []))
        if key in seen:
            continue
        alines.append(fmt(r))
        shown_adv.append(r)
        newly.add(key)
        if len(alines) >= cap:
            break
    if alines:
        blocks.append(
            "⚙️ 參考 · 這則訊息可能也適用（切題再載、不切題忽略）：\n" + "\n".join(alines)
        )

    # 觀察名單提醒（同 session 每條一次；不寫 suggestions.jsonl，不算失手）
    wlines = []
    for w in watch_hits:
        key = "watch|" + w.get("name", "")
        if key in seen:
            continue
        wlines.append("  - %s — %s" % (w.get("name", ""), w.get("note", "")))
        newly.add(key)
    if wlines:
        blocks.append(
            "🔭 評估紀錄簿觸發（非 skill——之前評估時記的「以後用得到」條件命中了，切題就提給 Stan）：\n"
            + "\n".join(wlines)
            + "\n  詳見 ~/.claude/skills/skill-routing/EVALUATIONS.md 對應列。"
        )

    if not blocks:
        return

    try:
        json.dump(sorted(seen | newly), open(sf, "w", encoding="utf-8"))
    except Exception:
        pass

    # 建議留痕（兩區都記）：供 Stop hook 對帳「建議過 vs 實際載入」→ misses.jsonl
    try:
        lg = os.path.join(STATE_DIR, "suggestions-%s.jsonl" % safe)
        with open(lg, "a", encoding="utf-8") as lf:
            for r in mand[:cap]:
                lf.write(json.dumps({"zone": "mandatory", "skills": r.get("skills", [])},
                                    ensure_ascii=False) + "\n")
            for r in shown_adv:
                lf.write(json.dumps({"zone": "soft", "skills": r.get("skills", [])},
                                    ensure_ascii=False) + "\n")
    except Exception:
        pass

    emit("\n\n".join(blocks))


try:
    main()
except Exception:
    pass
sys.exit(0)
