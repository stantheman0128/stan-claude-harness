#!/usr/bin/env python3
"""SessionStart watcher：偵測自上次 session 以來「新增」的 skill / 啟用 plugin，
若有新增就印一段提示到 stdout（會被當成 SessionStart context 注入），提醒用
skill-routing 重新評估重疊並把結果寫回 skill-routing 的 SKILL.md。

設計重點：
- 只在「有新增」時輸出；沒變動或只有移除時靜默。
- 每次都更新 snapshot，所以同一個新增只提示一次。
- 第一次跑（沒有 snapshot）只建立基準、不輸出。
- 任何錯誤都吞掉、exit 0，絕不弄垮 session 啟動。
"""
import json
import sys
from pathlib import Path

CLAUDE = Path.home() / ".claude"
SETTINGS = CLAUDE / "settings.json"
SKILLS = CLAUDE / "skills"
SNAP = CLAUDE / "skill-routing-snapshot.json"


def current_state():
    plugins, overridden_off = [], set()
    try:
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        plugins = sorted(k for k, v in (data.get("enabledPlugins") or {}).items() if v is True)
        overridden_off = {k for k, v in (data.get("skillOverrides") or {}).items() if v == "off"}
    except Exception:
        pass
    personal = []
    try:
        # skillOverrides=off 的視同不存在，這樣「停用」也會被當成移除偵測到
        personal = sorted(p.name for p in SKILLS.iterdir()
                          if p.is_dir() and (p / "SKILL.md").exists() and p.name not in overridden_off)
    except Exception:
        pass
    return {"plugins": plugins, "personal": personal}


def banner():
    """一律輸出的『系統啟用中』橫幅，讓 Stan 每個 session 看得到系統在跑 + 近期用過哪些 skill。"""
    recent = []
    try:
        usage = CLAUDE / "skill-usage"
        files = sorted(usage.glob("session-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in files[:4]:
            try:
                recent += (json.loads(p.read_text(encoding="utf-8")).get("skills_used") or [])
            except Exception:
                pass
    except Exception:
        pass
    seen, uniq = set(), []
    for s in recent:
        if s not in seen:
            seen.add(s); uniq.append(s)
    tail = ("；近期用過：" + "、".join(uniq[:6])) if uniq else "；近期未載入任何 skill"

    # 上一個 session 的 router 失手（建議了但沒被載入）→ 開場讓 Stan 與模型都看到
    miss_tail = ""
    try:
        usage = CLAUDE / "skill-usage"
        files = sorted(usage.glob("session-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            last = json.loads(files[0].read_text(encoding="utf-8"))
            if last.get("router_misses"):
                sid, names = last.get("session"), []
                mj = usage / "misses.jsonl"
                if mj.exists():
                    for line in mj.read_text(encoding="utf-8").splitlines()[-20:]:
                        try:
                            rec = json.loads(line)
                        except Exception:
                            continue
                        if rec.get("session") == sid:
                            names.append("/".join(rec.get("skills", [])) + ("(強制)" if rec.get("zone") == "mandatory" else ""))
                miss_tail = ("；⚠️ 上次 router 建議未被載入：" + "、".join(names[:4])) if names else \
                            ("；⚠️ 上次 router 失手 %d 次" % last["router_misses"])
    except Exception:
        pass

    return ("⚙️ [skill 系統啟用中] 關鍵字提醒(UserPromptSubmit) + 用量紀錄(Stop) + 失手對帳(misses) 運作中" + tail + miss_tail
            + "。（請在本 session 第一則回覆開頭把這行顯示給使用者一次，讓他確認系統在跑；之後不必重複。）")


def main():
    cur = current_state()
    prev = None
    if SNAP.exists():
        try:
            prev = json.loads(SNAP.read_text(encoding="utf-8"))
        except Exception:
            prev = None

    # 永遠把目前狀態寫回 snapshot（同一新增只提示一次）
    try:
        SNAP.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    print(banner())  # 一律印：每個 session 開場都讓 Stan 看得到系統啟用

    if prev is None:
        return 0  # 第一次：只建基準，橫幅照印、新增偵測不輸出

    new_plugins = [x for x in cur["plugins"] if x not in set(prev.get("plugins", []))]
    new_personal = [x for x in cur["personal"] if x not in set(prev.get("personal", []))]
    removed_plugins = [x for x in prev.get("plugins", []) if x not in set(cur["plugins"])]
    removed_personal = [x for x in prev.get("personal", []) if x not in set(cur["personal"])]
    if not (new_plugins or new_personal or removed_plugins or removed_personal):
        return 0

    lines = ["[skill-routing watch] 偵測到自上次 session 以來的 skill / plugin 變動："]
    if new_plugins:
        lines.append("  新啟用 plugin：" + ", ".join(new_plugins))
    if new_personal:
        lines.append("  新個人 skill：" + ", ".join(new_personal))
    if removed_plugins:
        lines.append("  移除/停用 plugin：" + ", ".join(removed_plugins))
    if removed_personal:
        lines.append("  移除/停用個人 skill：" + ", ".join(removed_personal))
    if new_plugins or new_personal:
        lines.append(
            "新增的請用 skill-routing skill 評估：先找出它跟哪些現有 skill 重疊，"
            "再實讀比品質（重疊≠新的較差：新的整體更好→設為預設；只在某子情境更好→路由那情境；舊的較好但新的有單點好想法→harvest 進舊檔；真重複沒贏→建議停用）。"
            "結果寫回 ~/.claude/skills/skill-routing/SKILL.md；若要停用 plugin / 改 settings，先問 Stan。"
        )
    if removed_plugins or removed_personal:
        lines.append(
            "移除/停用的請檢查 skill-routing 分流表：把受影響條目標 ❄️ 進冷藏區、預設主力失效的列改指還活著的替代，"
            "並依「編譯規範」重編譯 skill-rules.json 與全域 CLAUDE.md 第 1 條分流摘要，拔掉死引用。"
        )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
