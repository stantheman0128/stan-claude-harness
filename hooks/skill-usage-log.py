#!/usr/bin/env python
# Stop hook：解析本 session 的 transcript，記錄「真正透過 Skill 工具載入過哪些 skill」。
# 這是 ground-truth 對帳紀錄（不靠模型自述、不謊報），供「每個 session 用了哪些 skill」查核。
# best-effort：任何錯誤都 exit 0、不影響收尾。
import sys, os, json, re

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skill-usage")
OUT_DIR = os.path.abspath(OUT_DIR)


def skill_uses_from(content):
    found = []
    if not isinstance(content, list):
        return found
    for c in content:
        if not isinstance(c, dict):
            continue
        if c.get("type") == "tool_use" and str(c.get("name", "")).split("__")[-1] == "Skill":
            inp = c.get("input") or {}
            name = inp.get("skill") or inp.get("name") or inp.get("command")
            if name:
                found.append(str(name))
    return found


def main():
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    tp = data.get("transcript_path")
    session = data.get("session_id") or "default"
    if not tp or not os.path.exists(tp):
        return

    used = []
    with open(tp, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            msg = ev.get("message") if isinstance(ev.get("message"), dict) else ev
            used += skill_uses_from(msg.get("content") if isinstance(msg, dict) else None)

    # 去重保序
    seen, uniq = set(), []
    for s in used:
        if s not in seen:
            seen.add(s)
            uniq.append(s)

    os.makedirs(OUT_DIR, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(session))

    # router 失手對帳：suggestions-<session>.jsonl（skill-suggest.py 留痕）vs 實際載入。
    # 一筆建議列多個 skill = 任一被載入即算命中；全沒載 = miss。graphify 是 CLI 非 skill，不計。
    misses, mand_miss = [], 0
    try:
        sug_path = os.path.join(OUT_DIR, "suggestions-%s.jsonl" % safe)
        if os.path.exists(sug_path):
            used_set = set(uniq)
            seen_keys = set()
            with open(sug_path, encoding="utf-8") as sf:
                for line in sf:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    skills = [s for s in rec.get("skills", []) if s != "graphify"]
                    if not skills:
                        continue
                    key = "|".join(skills)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    if not any(s in used_set for s in skills):
                        misses.append({"zone": rec.get("zone", "?"), "skills": skills})
                        if rec.get("zone") == "mandatory":
                            mand_miss += 1
            if misses:
                with open(os.path.join(OUT_DIR, "misses.jsonl"), "a", encoding="utf-8") as mf:
                    for m in misses:
                        mf.write(json.dumps({"session": session, **m}, ensure_ascii=False) + "\n")
    except Exception:
        pass

    out = os.path.join(OUT_DIR, "session-%s.json" % safe)
    json.dump({"session": session, "count": len(uniq), "skills_used": uniq,
               "router_misses": len(misses), "router_mandatory_misses": mand_miss},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


try:
    main()
except Exception:
    pass
sys.exit(0)
