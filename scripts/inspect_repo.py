#!/usr/bin/env python
"""在陌生 repo 開 session 之前，先看它的 Claude 相關設定會做什麼。

用法：py -I ~/.claude/scripts/inspect_repo.py <repo 路徑>

只讀不執行：不跑 repo 裡的任何東西，檔案內容一律當資料印出（截斷、去掉控制字元）。
環境變數只印名字，不印值。
掃的範圍照 code.claude.com/docs 的 .claude 目錄說明和 plugin 參考：專案 .claude/ 底下會載入的資料夾，
以及 plugin 或 marketplace repo 的元件。文字檔不看副檔名一律掃；二進位檔只有圖片、字型、影音可以略過，
其他二進位檔、symlink、超過上限的檔都記成掃描不完整。
"""
import json
import os
import re
import sys
from pathlib import Path

MAX_BYTES = 300_000
MAX_FILES = 300
SNIFF = 8192
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
# 可改走代理、換 API 端點或注入程式的環境變數名稱
DANGER_ENV = re.compile(
    r"BASE_URL|PROXY|NODE_OPTIONS|^PATH$|LD_PRELOAD|DYLD_|PYTHONPATH|PYTHONSTARTUP|_URL$|ENDPOINT",
    re.IGNORECASE,
)
# 圖片、字型、影音的副檔名：內容真的是二進位才略過，其他二進位檔一律算掃不到
MEDIA_EXT = frozenset((
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".tif", ".tiff", ".avif",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".mp4", ".mov", ".webm", ".avi", ".mkv",
))
# 專案 .claude/ 底下 Claude Code 會載入的資料夾；hooks/ 不是載入位置，但 settings 的 hook 常呼叫這裡的腳本
CLAUDE_DIRS = ("commands", "agents", "skills", "hooks", "rules", "output-styles", "workflows", "agent-memory")
# plugin 根目錄的預設元件資料夾；bin/ 會放進 Bash 的 PATH，scripts/ 是 hook 常呼叫的腳本位置
PLUGIN_DIRS = ("skills", "commands", "agents", "hooks", "scripts", "output-styles", "workflows", "monitors", "bin")
INSTRUCTION_FILES = ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md", "AGENTS.md", ".claude/AGENTS.md")
EXEC, MCP, RISK = "hook 與會執行的設定", "MCP server", "可疑指令行"
COUNTS = {EXEC: 0, MCP: 0, RISK: 0}
# 讀不到、解析失敗、超過大小或檔數上限、二進位檔、symlink：掃描不完整，結論不能說安全
PROBLEMS = []
SEEN = set()          # 掃過或當設定解析過的檔，避免重複
PLUGINS_SEEN = set()  # 掃過的 plugin 根目錄
STATS = {"scanned": 0, "media": 0, "over": 0}
ROOT = Path(".")


def clean(text, cut=CUT):
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "?", str(text)).replace("\n", " ")
    return text if len(text) <= cut else text[:cut] + " ...(截斷)"


def rel(path):
    """給人看的路徑：盡量相對於 repo 根目錄，去掉控制字元。"""
    try:
        text = Path(path).relative_to(ROOT).as_posix() or "."
    except ValueError:
        text = str(path)
    return clean(text, 120)


def file_key(path):
    try:
        return os.path.normcase(str(Path(path).resolve()))
    except (OSError, RuntimeError):
        return os.path.normcase(str(Path(path).absolute()))


def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def is_link(path):
    """symlink 或 Windows junction：不跟進去，免得掃到 repo 外面。"""
    try:
        return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())
    except OSError:
        return True


def read_text(path):
    try:
        data = path.read_bytes()
    except OSError as e:
        PROBLEMS.append(f"讀不到 {rel(path)}（{clean(e, 60)}）")
        return None
    if len(data) > MAX_BYTES:
        PROBLEMS.append(f"{rel(path)} 超過 {MAX_BYTES} bytes，只看了前段")
        data = data[:MAX_BYTES]
    return data.decode("utf-8", errors="replace")


def load_json(path, kind=dict):
    SEEN.add(file_key(path))
    text = read_text(path)
    if text is None:
        return None, "讀不到"
    try:
        data = json.loads(text.lstrip("﻿"))
    except ValueError as e:
        PROBLEMS.append(f"{rel(path)} 解析失敗")
        return None, f"JSON 解析失敗：{clean(e, 80)}"
    if not isinstance(data, kind):
        want = "JSON 物件" if kind is dict else "JSON 物件或陣列"
        PROBLEMS.append(f"{rel(path)} 不是 {want}")
        return None, f"不是 {want}"
    return data, None


def hooks_report(hooks, out):
    """hook 設定（事件 -> matcher 陣列），每個會執行的東西印一行，回傳筆數。"""
    risk = 0
    for event, entries in hooks.items() if isinstance(hooks, dict) else []:
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            matcher = entry.get("matcher", "")
            for h in entry.get("hooks") or []:
                if isinstance(h, dict):
                    cmd = h.get("command") or h.get("url") or h.get("prompt") or h.get("type")
                    args = h.get("args") if isinstance(h.get("args"), list) else []
                    shown = " ".join([str(cmd)] + [str(a) for a in args])
                    out.append(f"  [hook] {clean(event, 40)} {clean(matcher, 40)} -> {clean(shown)}")
                    risk += 1
    return risk


def settings_report(path, out):
    data, err = load_json(path)
    if err:
        out.append(f"  {err}")
        return
    risk = 0
    hooks = data.get("hooks")
    if isinstance(hooks, dict):
        risk += hooks_report(hooks, out)
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
        names = [str(k) for k in env]
        danger = [n for n in names if DANGER_ENV.search(n)]
        out.append(f"  [env] 設了 {len(env)} 個變數：{clean(', '.join(names), 120)}")
        if danger:
            out.append(f"  [危險 env] {clean(', '.join(danger), 120)}（可改走代理、換 API 端點或注入程式）")
        risk += 1 + len(danger)
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
    COUNTS[EXEC] += risk


def mcp_servers_report(servers, out):
    for name, cfg in servers.items() if isinstance(servers, dict) else []:
        if not isinstance(cfg, dict):
            continue
        args = cfg.get("args") if isinstance(cfg.get("args"), list) else []
        target = cfg.get("url") or " ".join([str(cfg.get("command", ""))] + [str(a) for a in args])
        envs = cfg.get("env") if isinstance(cfg.get("env"), dict) else {}
        extra = f"（env：{', '.join(map(str, envs.keys()))}）" if envs else ""
        out.append(f"  [MCP] {clean(name, 40)} -> {clean(target)}{clean(extra, 80)}")
        if cfg.get("headersHelper"):
            out.append(f"  [會執行指令] {clean(name, 40)} headersHelper -> {clean(cfg.get('headersHelper'))}")
        COUNTS[MCP] += 1


def mcp_report(path, out):
    """根目錄的 .mcp.json。plugin 的 .mcp.json 可以不包 mcpServers，所以沒有這個鍵就把整個物件當 server 表。"""
    data, err = load_json(path)
    if err:
        out.append(f"  {err}")
        return
    mcp_servers_report(data.get("mcpServers") if isinstance(data.get("mcpServers"), dict) else data, out)


def lsp_report(servers, out):
    for name, cfg in servers.items() if isinstance(servers, dict) else []:
        if not isinstance(cfg, dict):
            continue
        args = cfg.get("args") if isinstance(cfg.get("args"), list) else []
        envs = cfg.get("env") if isinstance(cfg.get("env"), dict) else {}
        extra = f"（env：{', '.join(map(str, envs.keys()))}）" if envs else ""
        cmd = " ".join([str(cfg.get("command", ""))] + [str(a) for a in args])
        out.append(f"  [LSP] {clean(name, 40)} -> {clean(cmd)}{clean(extra, 80)}")
        COUNTS[EXEC] += 1


def monitors_report(items, out):
    for m in items if isinstance(items, list) else []:
        if isinstance(m, dict):
            when = clean(m.get("when", "always"), 40)
            out.append(f"  [monitor] {clean(m.get('name', '?'), 40)}（{when}）-> {clean(m.get('command'))}")
            COUNTS[EXEC] += 1


def config_file_report(path, kind, out):
    """plugin 的 hooks、MCP、LSP、monitor 設定檔。沒有外層包裝的也照樣列出來，寧可多列。"""
    out.append(f"  {rel(path)}")
    data, err = load_json(path, (dict, list) if kind == "monitors" else dict)
    if err:
        out.append(f"    {err}")
        return
    if kind == "hooks":
        COUNTS[EXEC] += hooks_report(data.get("hooks") if isinstance(data.get("hooks"), dict) else data, out)
    elif kind == "mcp":
        mcp_servers_report(data.get("mcpServers") if isinstance(data.get("mcpServers"), dict) else data, out)
    elif kind == "lsp":
        lsp_report(data.get("lspServers") if isinstance(data.get("lspServers"), dict) else data, out)
    else:
        monitors_report(data.get("monitors") if isinstance(data, dict) else data, out)


def risky_text(text, label, out):
    for i, line in enumerate(text.splitlines(), 1):
        if RISKY.search(line):
            out.append(f"    [可疑] {clean(label, 120)} 第 {i} 行：{clean(line)}")
            COUNTS[RISK] += 1


def scan_file(path, out):
    """掃一個檔的可疑行。文字檔不看副檔名一律掃；二進位檔只有圖片字型影音可以略過，其餘記成掃不到。"""
    if is_link(path):
        PROBLEMS.append(f"{rel(path)} 是 symlink，沒跟進去掃")
        return
    key = file_key(path)
    if key in SEEN:
        return
    SEEN.add(key)
    try:
        with path.open("rb") as fh:
            head = fh.read(SNIFF)
    except OSError as e:
        PROBLEMS.append(f"讀不到 {rel(path)}（{clean(e, 60)}）")
        return
    if b"\x00" in head:
        if path.suffix.lower() in MEDIA_EXT:
            STATS["media"] += 1
        else:
            PROBLEMS.append(f"{rel(path)} 是二進位檔，沒辦法掃")
        return
    if STATS["scanned"] >= MAX_FILES:
        STATS["over"] += 1
        return
    STATS["scanned"] += 1
    text = read_text(path)
    if text is not None:
        risky_text(text, rel(path), out)


def walk_files(folder):
    """資料夾底下所有檔（含子資料夾）。symlink、junction 不跟進去，讀不到的資料夾也記下來。"""
    files = []

    def failed(err):
        PROBLEMS.append(f"讀不到資料夾 {rel(getattr(err, 'filename', None) or folder)}")

    for dirpath, dirnames, filenames in os.walk(folder, onerror=failed):
        here = Path(dirpath)
        for name in sorted(dirnames):
            if is_link(here / name):
                PROBLEMS.append(f"{rel(here / name)} 是 symlink，沒跟進去掃")
                dirnames.remove(name)
        dirnames.sort()
        files.extend(here / name for name in sorted(filenames))
    return files


def scan_folder(folder, out):
    if is_link(folder):
        PROBLEMS.append(f"{rel(folder)} 是 symlink，沒跟進去掃")
        return []
    files = walk_files(folder)
    out.append(f"  {rel(folder)}/：{len(files)} 個檔：{clean(', '.join(p.name for p in files[:20]), 200)}")
    for path in files:
        scan_file(path, out)
    return files


def component_path(base, value, where, out):
    """plugin 元件路徑換成實際位置。resolve 之前逐層檢查 symlink、junction，有就不跟；
    跑出 plugin 根目錄的也記成掃描不完整。不存在的路徑 Claude Code 也不會載入，只印一行。"""
    if base is None:
        out.append(f"  [略過] {where}：{clean(value, 80)} 在外部 plugin 裡，這個 repo 沒有那些檔")
        return None
    try:
        base = base.resolve()
        cur = base
        for part in Path(value).parts:
            cur = cur / part
            if part not in (".", "..") and is_link(cur):
                PROBLEMS.append(f"{rel(cur)} 是 symlink，沒跟進去掃（{where}：{clean(value, 80)}）")
                return None
        path = (base / value).resolve()
    except (OSError, RuntimeError, ValueError):
        PROBLEMS.append(f"{where} 的路徑看不懂：{clean(value, 80)}")
        return None
    if not path.is_relative_to(base):
        PROBLEMS.append(f"{where} 指到 plugin 外面：{clean(value, 80)}")
        out.append(f"  [略過] {where} 指到 plugin 外面：{clean(value, 80)}（沒掃，記成掃描不完整）")
        return None
    if not path.exists():
        out.append(f"  [略過] {where} 指到不存在的路徑：{clean(value, 80)}")
        return None
    return path


def inline_hooks_report(hooks, where, out):
    """plugin.json 或 marketplace 條目的 inline hooks。照 hooks.json 寫法包了外層 {"hooks": {...}} 就先拆掉；
    事件的值不是陣列、或整個物件認不出任何 hook，都記成掃描不完整。"""
    maps = [hooks]
    if isinstance(hooks.get("hooks"), dict):
        maps = [hooks["hooks"], {k: v for k, v in hooks.items() if k != "hooks"}]
    found = 0
    for m in maps:
        for event, entries in m.items():
            if not isinstance(entries, list):
                PROBLEMS.append(f"{where} 的 hooks.{clean(event, 40)} 不是陣列，看不懂")
        found += hooks_report(m, out)
    if not found:
        PROBLEMS.append(f"{where} 的 hooks 裡認不出任何 hook")
    COUNTS[EXEC] += found


def manifest_report(data, base, where, out):
    """plugin.json 或 marketplace 條目宣告的元件：hook、MCP、LSP、monitor 直接列出，其他路徑照掃。"""
    for key, kind in (("hooks", "hooks"), ("mcpServers", "mcp"), ("lspServers", "lsp")):
        for item in as_list(data.get(key)):
            if isinstance(item, dict):
                if kind == "hooks":
                    inline_hooks_report(item, where, out)
                elif kind == "mcp":
                    mcp_servers_report(item, out)
                else:
                    lsp_report(item, out)
            elif isinstance(item, str) and kind == "mcp" and item.lower().startswith(("https://", "http://")):
                out.append(f"  [MCP bundle] {where} 會下載：{clean(item)}")
                COUNTS[MCP] += 1
            elif isinstance(item, str):
                path = component_path(base, item, f"{where} {key}", out)
                if path is None:
                    continue
                if path.suffix.lower() in (".mcpb", ".dxt"):
                    PROBLEMS.append(f"{rel(path)} 是 MCP bundle 壓縮檔，沒辦法掃")
                elif path.is_file():
                    config_file_report(path, kind, out)
                else:
                    PROBLEMS.append(f"{where} 的 {key} 不是檔案：{rel(path)}")
            else:
                PROBLEMS.append(f"{where} 的 {key} 格式看不懂")
    experimental = data.get("experimental") if isinstance(data.get("experimental"), dict) else {}
    for item in (data.get("monitors"), experimental.get("monitors")):
        if isinstance(item, list):
            monitors_report(item, out)
        elif isinstance(item, str):
            path = component_path(base, item, f"{where} monitors", out)
            if path is not None and path.is_file():
                config_file_report(path, "monitors", out)
        elif item is not None:
            PROBLEMS.append(f"{where} 的 monitors 格式看不懂")
    commands = data.get("commands")
    keys = ["agents", "skills", "outputStyles", "workflows"]
    if isinstance(commands, dict):
        for name, spec in commands.items():
            spec = spec if isinstance(spec, dict) else {}
            if isinstance(spec.get("content"), str):
                risky_text(spec["content"], f"{where} commands.{name}", out)
            elif isinstance(spec.get("source"), str):
                path = component_path(base, spec["source"], f"{where} commands.{clean(name, 40)}", out)
                if path is not None:
                    scan_folder(path, out) if path.is_dir() else scan_file(path, out)
            else:
                PROBLEMS.append(f"{where} 的 commands.{clean(name, 40)} 格式看不懂")
    else:
        keys.append("commands")
    for key in keys:
        for item in as_list(data.get(key)):
            if not isinstance(item, str):
                PROBLEMS.append(f"{where} 的 {key} 格式看不懂")
                continue
            path = component_path(base, item, f"{where} {key}", out)
            if path is None:
                continue
            if key == "skills" and path == base.resolve():
                # "." 代表 plugin 根目錄本身：根目錄的 SKILL.md 和每個 <name>/SKILL.md 資料夾
                if (path / "SKILL.md").is_file():
                    scan_file(path / "SKILL.md", out)
                for child in sorted(p for p in path.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()):
                    scan_folder(child, out)
            elif path.is_dir():
                scan_folder(path, out)
            else:
                scan_file(path, out)


def plugin_report(proot, label, out):
    """plugin 根目錄：plugin.json、hooks/hooks.json、.mcp.json、.lsp.json、monitors、預設元件資料夾。"""
    key = file_key(proot)
    if key in PLUGINS_SEEN:
        return
    PLUGINS_SEEN.add(key)
    out.append(f"plugin {label}")
    manifest = proot / ".claude-plugin" / "plugin.json"
    if manifest.is_file():
        out.append(f"  {rel(manifest)}")
        data, err = load_json(manifest)
        if err:
            out.append(f"    {err}")
        else:
            manifest_report(data, proot, rel(manifest), out)
    for name, kind in (("hooks/hooks.json", "hooks"), (".mcp.json", "mcp"), (".lsp.json", "lsp"),
                       ("monitors/monitors.json", "monitors")):
        path = proot / name
        if path.is_file() and file_key(path) not in SEEN:
            config_file_report(path, kind, out)
    if (proot / "SKILL.md").is_file():
        scan_file(proot / "SKILL.md", out)
    for sub in PLUGIN_DIRS:
        folder = proot / sub
        if not (folder.is_dir() or is_link(folder)):
            continue
        files = scan_folder(folder, out)
        if sub == "bin":
            for path in files:
                out.append(f"  [PATH 執行檔] {rel(path)}（plugin 啟用時放進 Bash 的 PATH）")
                COUNTS[EXEC] += 1


def marketplace_report(root, out):
    """marketplace.json：本地 plugin 照 plugin 規則掃，外部來源和會執行的欄位列出來。"""
    path = root / ".claude-plugin" / "marketplace.json"
    out.append(f"marketplace {rel(path)}")
    data, err = load_json(path)
    if err:
        out.append(f"  {err}")
        return
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    plugin_root = meta.get("pluginRoot") if isinstance(meta.get("pluginRoot"), str) else None
    for entry in data.get("plugins") if isinstance(data.get("plugins"), list) else []:
        if not isinstance(entry, dict):
            continue
        where = f"marketplace.json {clean(entry.get('name', '?'), 40)}"
        src = entry.get("source")
        base = None
        if isinstance(src, str):
            value = src
            if plugin_root and src not in (".", "") and "/" not in src:
                value = f"{plugin_root.rstrip('/')}/{src}"  # pluginRoot 底下的裸名稱
            path = component_path(root, value, f"{where} source", out)
            if path is not None and path.is_dir():
                base = path
                plugin_report(path, f"{rel(path)}（{where}）", out)
        else:
            kind = src.get("source") if isinstance(src, dict) else None
            if kind == "command":
                out.append(f"  [會執行指令] {where} 的來源是 command -> {clean(src.get('command'))}")
            else:
                out.append(f"  [外部 plugin] {where} -> {clean(json.dumps(src, ensure_ascii=False), 120)}")
            COUNTS[EXEC] += 1
        if entry.get("headersHelper"):
            out.append(f"  [會執行指令] {where} headersHelper -> {clean(entry.get('headersHelper'))}")
            COUNTS[EXEC] += 1
        manifest_report(entry, base, where, out)


def main():
    global ROOT
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
    ROOT = root

    out = []
    claude_dir = root / ".claude"

    for name in ("settings.json", "settings.local.json"):
        path = claude_dir / name
        if path.is_file():
            out.append(f".claude/{name}")
            settings_report(path, out)

    mcp = root / ".mcp.json"
    if mcp.is_file():
        out.append(".mcp.json")
        mcp_report(mcp, out)

    out.append("指令檔")
    for name in INSTRUCTION_FILES:
        path = root / name
        if path.is_file():
            SEEN.add(file_key(path))
            text = read_text(path) or ""
            out.append(f"  {name}：{len(text.splitlines())} 行")
            risky_text(text, name, out)

    for sub in CLAUDE_DIRS:
        folder = claude_dir / sub
        if folder.is_dir() or is_link(folder):
            scan_folder(folder, out)

    plugin_dir = root / ".claude-plugin"
    if plugin_dir.is_dir():
        listed = ", ".join(sorted(p.name for p in plugin_dir.iterdir()))
        out.append(f"  .claude-plugin/：{clean(listed, 160)}（這個 repo 是 plugin 或 marketplace）")
        plugin_report(root, "（repo 根目錄）", out)
        if (plugin_dir / "marketplace.json").is_file():
            marketplace_report(root, out)

    if STATS["over"]:
        PROBLEMS.append(f"有 {STATS['over']} 個檔超過 {MAX_FILES} 個上限沒掃")

    total = sum(COUNTS.values())
    print(f"inspect_repo：{root}")
    print("重點：" + "、".join(f"{k} {v}" for k, v in COUNTS.items()))
    print(f"掃了 {STATS['scanned']} 個檔，略過 {STATS['media']} 個圖片、字型或影音檔")
    if PROBLEMS:
        more = f"（共 {len(PROBLEMS)} 項，完整清單在最後）" if len(PROBLEMS) > 5 else ""
        print("掃描不完整：" + "；".join(PROBLEMS[:5]) + more)
        print("建議：當成有風險，先把結果貼給 Stan 看過，再在這個 repo 開 session。")
    elif total:
        print("建議：先把 hook、MCP、可疑行貼給 Stan 看過，再在這個 repo 開 session。")
    else:
        print("建議：沒看到會自動執行的設定，可以開 session。")
    print()
    print("\n".join(out))
    if len(PROBLEMS) > 5:
        print("\n掃描不完整的項目：")
        print("\n".join(f"  - {p}" for p in PROBLEMS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
