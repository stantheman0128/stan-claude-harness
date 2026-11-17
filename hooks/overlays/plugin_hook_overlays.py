"""Rewrite third-party plugin hooks.json files into exec form (no Git Bash launcher).

Why: on this machine every shell-form hook costs bash launcher + bash + conhost before the real
interpreter starts, and Defender scans each new process (measured 2026-11-17: shell chain ~36 ms
vs direct python ~12 ms per hook). Plugin updates replace the cache folder and undo this, so run
it again after any plugin update:

    python -I C:/Users/stans/.claude/hooks/overlays/plugin_hook_overlays.py          # apply
    python -I C:/Users/stans/.claude/hooks/overlays/plugin_hook_overlays.py --check  # report only

Idempotent. Only commands that match a known launcher pattern are rewritten; anything else is left
as is and reported, so an upstream change fails safe (it keeps the slow-but-working shell form).
The first time a file is changed the original is kept next to it as hooks.json.orig.
quota-pacer is Stan's own plugin and is fixed in its source instead (local-plugins/quota-pacer).
"""
import json
import os
import re
import shutil
import sys

PYW = "C:/Python313/pythonw.exe"   # no console: only for hooks that never start child processes (none here now)
PY = "C:/Python313/python.exe"     # console kept: child processes (git, pip, claude) inherit a hidden one
NODE = "C:/Program Files/nodejs/node.exe"
ROOT = "${CLAUDE_PLUGIN_ROOT}"
INSTALLED = os.path.expanduser("~/.claude/plugins/installed_plugins.json")

# impeccable's hook.mjs only inspects these (hook-lib.mjs ALLOWED_EXTS, 3.9.1). `if` takes one
# permission rule and no brace globs; `Edit(*.tsx)` matches at any depth, also outside the project.
IMPECCABLE_EXTS = ("tsx", "jsx", "html", "htm", "vue", "svelte", "astro",
                   "css", "scss", "sass", "less", "ts", "js")
IMPECCABLE_TOOLS = ("Edit", "Write", "MultiEdit")


def te(cmd):
    # Upstream ships the bare quoted path; an older local patch had prefixed `sh`.
    # python.exe, not pythonw: te starts detached `te` processes with sys.executable, and those run
    # git and `claude -p`. Under pythonw they have no console, so each of those would open a visible
    # window (winspawn.py says so; verifier reproduced consoleCP=0, 2026-11-17).
    if cmd in (f'"{ROOT}/scripts/te-hook"', f'sh "{ROOT}/scripts/te-hook"'):
        return PY, ["-X", "utf8", f"{ROOT}/scripts/te_bootstrap.py", "hook"]


SG = re.compile(r'^bash "\$\{CLAUDE_PLUGIN_ROOT\}/hooks/sg-python\.sh" "(\$\{CLAUDE_PLUGIN_ROOT\}/hooks/[\w.]+\.py)"$')


def sg(cmd):
    m = SG.match(cmd)
    if m:
        return PY, ["-X", "utf8", m.group(1)]


def imp(cmd):
    if cmd == f'node "{ROOT}/skills/impeccable/scripts/hook.mjs"':
        return NODE, [f"{ROOT}/skills/impeccable/scripts/hook.mjs"]


PLUGINS = {
    "tokeneconomizer@tokeneconomizer": te,
    "security-guidance@claude-plugins-official": sg,
    "impeccable@impeccable": imp,
}


def convert(h, rule):
    """Exec-form copy of hook h, or None when h is already converted or unknown."""
    if h.get("type") != "command" or "args" in h:
        return None
    r = rule(h.get("command", ""))
    if not r:
        return None
    nh = {"type": "command", "command": r[0], "args": r[1]}
    nh.update({k: v for k, v in h.items() if k not in ("type", "command")})
    return nh


def impeccable_filters(groups):
    """Split impeccable's single Edit|Write|MultiEdit hook into one entry per tool and extension,
    each with an `if`, so node only starts for files it would inspect."""
    out = []
    for g in groups:
        hs = []
        for h in g["hooks"]:
            if (h.get("type") == "command" and "if" not in h and h.get("command") == NODE
                    and h.get("args", [""])[-1].endswith("/scripts/hook.mjs")):
                for t in IMPECCABLE_TOOLS:
                    for e in IMPECCABLE_EXTS:
                        hs.append(dict(h, **{"if": f"{t}(*.{e})"}))
            else:
                hs.append(h)
        out.append(dict(g, hooks=hs))
    return out


def process(key, rule, check):
    inst = json.load(open(INSTALLED, encoding="utf-8"))["plugins"].get(key)
    if not inst:
        print(f"{key}: not installed")
        return
    path = os.path.join(inst[0]["installPath"], "hooks", "hooks.json")
    raw = open(path, encoding="utf-8").read()
    d = json.loads(raw)
    changed, unknown = 0, []
    for ev, groups in d.get("hooks", {}).items():
        for g in groups:
            for i, h in enumerate(g["hooks"]):
                nh = convert(h, rule)
                if nh:
                    g["hooks"][i] = nh
                    changed += 1
                elif h.get("type") == "command" and "args" not in h:
                    unknown.append(f"{ev}: {h.get('command')}")
        if key.startswith("impeccable@"):
            before = sum(len(g["hooks"]) for g in groups)
            d["hooks"][ev] = groups = impeccable_filters(groups)
            changed += sum(len(g["hooks"]) for g in groups) - before
    ver = inst[0].get("version")
    for u in unknown:
        print(f"{key} {ver}: left as shell form (pattern unknown): {u}")
    if not changed:
        print(f"{key} {ver}: already in exec form" if not unknown else f"{key} {ver}: nothing to rewrite")
        return
    if check:
        print(f"{key} {ver}: {changed} hook(s) would change")
        return
    if not os.path.exists(path + ".orig"):
        shutil.copy2(path, path + ".orig")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    print(f"{key} {ver}: rewrote {changed} hook(s) -> {path}")


if __name__ == "__main__":
    check = "--check" in sys.argv
    for k, rule in PLUGINS.items():
        process(k, rule, check)
