#!/usr/bin/env python
"""在陌生 repo 開 session 之前，先看它的 Claude 相關設定會做什麼。

用法：py -I ~/.claude/scripts/inspect_repo.py <repo 路徑>

只讀不執行：不跑 repo 裡的任何東西，檔案內容一律當資料印出（截斷、去掉控制字元）。
環境變數只印名字，不印值。
"""
import json
import re
import sys
from pathlib import Path

MAX_BYTES = 300_000
MAX_FILES = 60
CUT = 160
RISKY = re.compile(
    r"curl |wget |Invoke-WebRequest|\biwr\b|Invoke-Expression|\biex\b|bash -c|sh -c|"
    r"powershell|base64|\beval\b|rm -rf|chmod |sudo |--no-verify|dangerously|"
    r"ignore (all |any )?(previous|prior) instructions|without asking|auto-?approve|do not tell",
    re.IGNORECASE,
)
EXEC_KEYS = ("apiKeyHelper", "statusLine", "awsAuthRefresh", "awsCredentialExport", "otelHeadersHelper")
PLUGIN_KEYS = ("enabledPlugins", "extraKnownMarketplaces", "enableAllProjectMcpServers", "enabledMcpjsonServers")
BROAD_RULES = ("Bash", "Bash(*)", "WebFetch", "Write", "Edit")


def clean(text, cut=CUT):
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "?", str(text)).replace("\n", " ")
    return text if len(text) <= cut else text[:cut] + " ...(截斷)"


def read_text(path):
    try:
        return path.read_bytes()[:MAX_BYTES].decode("utf-8", errors="replace")
    except OSError:
        return None


def load_json(path):
    text = read_text(path)
    if text is None:
        return None, "讀不到"
    try:
        data = json.loads(text)
    except ValueError as e:
        return None, f"JSON 解析失敗：{clean(e, 80)}"
    return (data, None) if isinstance(data, dict) else (None, "不是 JSON 物件")


def settings_report(path, out):
    data, err = load_json(path)
    if err:
        out.append(f"  {err}")
        return 0
    risk = 0
    hooks = data.get("hooks")
    if isinstance(hooks, dict):
        for event, entries in hooks.items():
            for entry in entries if isinstance(entries, list) else []:
                if not isinstance(entry, dict):
                    continue
                matcher = entry.get("matcher", "")
                for h in entry.get("hooks") or []:
                    if isinstance(h, dict):
                        cmd = h.get("command") or h.get("url") or h.get("prompt") or h.get("type")
                        out.append(f"  [hook] {event} {clean(matcher, 40)} -> {clean(cmd)}")
                        risk += 1
    perms = data.get("permissions") if isinstance(data.get("permissions"), dict) else {}
    allow = perms.get("allow") if isinstance(perms.get("allow"), list) else []
    for rule in allow:
        r = str(rule)
        if r in BROAD_RULES or (r.startswith("Bash(") and "*" in r):
            out.append(f"  [寬權限] {clean(r, 80)}")
            risk += 1
    if perms.get("defaultMode"):
        out.append(f"  [權限模式] defaultMode = {clean(perms.get('defaultMode'), 40)}")
        risk += 1
    env = data.get("env")
    if isinstance(env, dict) and env:
        out.append(f"  [env] 設了 {len(env)} 個變數：{clean(', '.join(map(str, env.keys())), 120)}")
    for key in EXEC_KEYS:
        value = data.get(key)
        if value:
            cmd = value.get("command") if isinstance(value, dict) else value
            out.append(f"  [會執行指令] {key} -> {clean(cmd)}")
            risk += 1
    for key in PLUGIN_KEYS:
        if data.get(key):
            out.append(f"  [plugin/MCP] {key} -> {clean(json.dumps(data[key], ensure_ascii=False), 120)}")
            risk += 1
    return risk


def mcp_report(path, out):
    data, err = load_json(path)
    if err:
        out.append(f"  {err}")
        return 0
    servers = data.get("mcpServers") if isinstance(data.get("mcpServers"), dict) else {}
    count = 0
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        args = cfg.get("args") if isinstance(cfg.get("args"), list) else []
        target = cfg.get("url") or " ".join([str(cfg.get("command", ""))] + [str(a) for a in args])
        envs = cfg.get("env") if isinstance(cfg.get("env"), dict) else {}
        extra = f"（env：{', '.join(map(str, envs.keys()))}）" if envs else ""
        out.append(f"  [MCP] {clean(name, 40)} -> {clean(target)}{clean(extra, 80)}")
        count += 1
    return count


def risky_lines(path, label, out):
    text = read_text(path)
    if text is None:
        return 0
    hits = 0
    for i, line in enumerate(text.splitlines(), 1):
        if RISKY.search(line):
            out.append(f"    [可疑] {label} 第 {i} 行：{clean(line)}")
            hits += 1
    return hits


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    if len(sys.argv) != 2:
        print("用法：py -I inspect_repo.py <repo 路徑>")
        return 2
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"找不到資料夾：{root}")
        return 2

    out = []
    counts = {"hook 與會執行的設定": 0, "MCP server": 0, "可疑指令行": 0}
    claude_dir = root / ".claude"

    for name in ("settings.json", "settings.local.json"):
        path = claude_dir / name
        if path.is_file():
            out.append(f".claude/{name}")
            counts["hook 與會執行的設定"] += settings_report(path, out)

    mcp = root / ".mcp.json"
    if mcp.is_file():
        out.append(".mcp.json")
        counts["MCP server"] += mcp_report(mcp, out)

    out.append("指令檔")
    for rel in ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md", "AGENTS.md"):
        path = root / rel
        if path.is_file():
            text = read_text(path) or ""
            out.append(f"  {rel}：{len(text.splitlines())} 行")
            counts["可疑指令行"] += risky_lines(path, rel, out)

    scanned = 0
    for sub in ("commands", "agents", "skills", "hooks"):
        folder = claude_dir / sub
        if not folder.is_dir():
            continue
        files = sorted(p for p in folder.rglob("*") if p.is_file())
        out.append(f"  .claude/{sub}/：{len(files)} 個檔：{clean(', '.join(p.name for p in files[:20]), 200)}")
        for path in files:
            if scanned >= MAX_FILES:
                break
            if path.suffix.lower() in (".md", ".sh", ".ps1", ".py", ".js", ".json"):
                scanned += 1
                counts["可疑指令行"] += risky_lines(path, path.relative_to(root).as_posix(), out)

    plugin_dir = root / ".claude-plugin"
    if plugin_dir.is_dir():
        listed = ", ".join(sorted(p.name for p in plugin_dir.iterdir()))
        out.append(f"  .claude-plugin/：{clean(listed, 160)}（這個 repo 是 plugin 或 marketplace）")

    total = sum(counts.values())
    print(f"inspect_repo：{root}")
    print("重點：" + "、".join(f"{k} {v}" for k, v in counts.items()))
    if total:
        print("建議：先把 hook、MCP、可疑行貼給 Stan 看過，再在這個 repo 開 session。")
    else:
        print("建議：沒看到會自動執行的設定，可以開 session。")
    print()
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
