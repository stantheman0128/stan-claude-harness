"""Audit interim vs final assistant text per turn in Claude Code transcripts.

Usage: py -I -X utf8 codex-style-audit.py SINCE OUT [CUTOFF]
  SINCE   YYYY-MM-DD, only turns from this date on (and files modified since then)
  OUT     report path
  CUTOFF  ISO UTC timestamp (e.g. 2026-11-23T09:24:24Z). Codex turns in transcripts that
          started at or after it count as codex-v2, earlier ones as codex-v1. Claude Code reads
          style files at startup, so only sessions started after an edit are sure to have it.

Only turns whose prompt contains Chinese are counted, to keep automated English runs out.
Created 2026-11-23 for the codex output style audits (first run: 2026-11-23, 745 files).
"""
import json, os, re, sys, time, random

ROOT = os.path.expanduser("~/.claude/projects")
SINCE_DAY = sys.argv[1]
SINCE = time.mktime(time.strptime(SINCE_DAY, "%Y-%m-%d"))
OUT = sys.argv[2]
CUTOFF = sys.argv[3] if len(sys.argv) > 3 else "9999"
BACKREF = re.compile(r"如上所述|如前所述|前面提到|上面提到|如上|見上")
FINDING = re.compile(r"找到|查到|原因|結論|發現|結果|通過|失敗|是因為|沒有問題|確認了|看起來|應該是"
                     r"|found|turns out|because|passes|fails", re.I)
ANNOUNCE = re.compile(r"^(Let me|I'll|Using |我先|我來|先來|讓我)")
CJK = re.compile(r"[一-鿿]")
GROUPS = ("codex-v2", "codex-v1", "default")


def is_prompt(r):
    if r.get("type") != "user" or r.get("isSidechain") or r.get("isMeta"):
        return False
    c = (r.get("message") or {}).get("content")
    if isinstance(c, str):
        return not c.startswith("<")
    if isinstance(c, list):
        return any(b.get("type") == "text" for b in c) and not any(b.get("type") == "tool_result" for b in c)
    return False


def file_start(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"timestamp"' in line:
                try:
                    ts = json.loads(line).get("timestamp")
                except Exception:
                    continue
                if ts:
                    return ts
    return ""


def turns(path):
    cur, pending = None, None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"assistant"' not in line and '"user"' not in line and '"output_style"' not in line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            t = r.get("type")
            att = r.get("attachment")
            if t == "attachment" and isinstance(att, dict) and att.get("type") == "output_style":
                # The style attachment can land just before or just after the prompt.
                pending = att.get("style")
                if cur is not None:
                    cur["style"] = pending
                continue
            if is_prompt(r):
                if cur:
                    yield cur
                c = (r.get("message") or {}).get("content")
                txt = c if isinstance(c, str) else " ".join(b.get("text", "") for b in c if b.get("type") == "text")
                cur = {"ts": r.get("timestamp", ""), "style": pending, "blocks": [], "prompt": txt}
                continue
            if t == "assistant":
                pending = None
                if cur is not None and not r.get("isSidechain"):
                    for b in (r.get("message") or {}).get("content") or []:
                        if b.get("type") == "text" and b.get("text", "").strip():
                            cur["blocks"].append(("text", b["text"].strip()))
                        elif b.get("type") == "tool_use":
                            cur["blocks"].append(("tool", b.get("name")))
    if cur:
        yield cur


def split(turn):
    b = turn["blocks"]
    last_tool = max((i for i, x in enumerate(b) if x[0] == "tool"), default=-1)
    interim = [x[1] for i, x in enumerate(b) if x[0] == "text" and i < last_tool]
    final = [x[1] for i, x in enumerate(b) if x[0] == "text" and i > last_tool]
    return interim, final, last_tool >= 0


files = []
for d, _, fs in os.walk(ROOT):
    if "subagents" in d:
        continue
    for f in fs:
        p = os.path.join(d, f)
        if f.endswith(".jsonl") and os.path.getmtime(p) >= SINCE:
            files.append(p)

samples = {k: [] for k in GROUPS}
sessions = {k: set() for k in GROUPS}
agg = {k: {"turns": 0, "tool_turns": 0, "interim": 0, "interim_chars": 0, "interim_long": 0,
           "interim_multiline": 0, "announce": 0, "finding": 0, "chatty_turns": 0,
           "final_chars": 0, "finals": 0, "backref": 0, "no_final": 0} for k in GROUPS}
for p in files:
    started = file_start(p)
    for tn in turns(p):
        if tn["ts"] < SINCE_DAY or not CJK.search(tn.get("prompt", "")):
            continue
        if tn["style"] == "codex":
            key = "codex-v2" if started >= CUTOFF else "codex-v1"
        else:
            key = "default"
        interim, final, tools = split(tn)
        a = agg[key]
        a["turns"] += 1
        sessions[key].add(p)
        if not tools:
            continue
        a["tool_turns"] += 1
        a["interim"] += len(interim)
        a["chatty_turns"] += len(interim) >= 6
        for t in interim:
            a["interim_chars"] += len(t)
            a["interim_long"] += len(t) > 80
            a["interim_multiline"] += "\n" in t
            a["announce"] += bool(ANNOUNCE.match(t))
            a["finding"] += bool(FINDING.search(t))
            samples[key].append((os.path.basename(p)[:8], t))
        if final:
            ft = "\n".join(final)
            a["finals"] += 1
            a["final_chars"] += len(ft)
            a["backref"] += bool(BACKREF.search(ft))
        else:
            a["no_final"] += 1

with open(OUT, "w", encoding="utf-8") as o:
    o.write(f"files scanned: {len(files)}; since {SINCE_DAY}; cutoff {CUTOFF}\n\n")
    for k, a in agg.items():
        ti = max(a["tool_turns"], 1)
        ni = max(a["interim"], 1)
        o.write(f"== {k} ({len(sessions[k])} sessions) ==\n")
        o.write(f"turns {a['turns']}, with tools {a['tool_turns']}\n")
        o.write(f"interim msgs per tool-turn {a['interim'] / ti:.2f}; avg chars {a['interim_chars'] / ni:.0f}; "
                f">80 chars {a['interim_long'] / ni:.0%}; multi-line {a['interim_multiline'] / ni:.0%}; "
                f"announce-style {a['announce'] / ni:.0%}; finding-like {a['finding'] / ni:.0%}; "
                f"turns with 6+ interim {a['chatty_turns'] / ti:.0%}\n")
        o.write(f"finals {a['finals']}, avg chars {a['final_chars'] / max(a['finals'], 1):.0f}, "
                f"back-references {a['backref']}, tool-turns without final text {a['no_final']} "
                f"({a['no_final'] / ti:.0%})\n\n")
    random.seed(1)
    for k in GROUPS:
        o.write(f"\n== sample interim msgs ({k}) ==\n")
        for s, t in random.sample(samples[k], min(30, len(samples[k]))):
            o.write(f"[{s}] {t[:220].replace(chr(10), ' / ')}\n")
