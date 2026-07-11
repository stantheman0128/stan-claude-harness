#!/usr/bin/env python3
"""polish_srt.py <in.srt> <out.srt> [glossary.txt] — 輕潤色字幕。
通用修正：單獨 i→I、i'm/i've/i'd/i'll→大寫。不動句首（避免誤傷被拆行的續行）。
選用 glossary.txt：每行 `wrong=>Right`（大小寫不敏感的整詞替換），放專有名詞，例如：
    colonist=>Colonist
    web socket=>WebSocket
    ui ux=>UI/UX
"""
import re, sys, pathlib

subs = [(re.compile(r"\bi\b"), "I"),
        (re.compile(r"\bi'm\b", re.I), "I'm"), (re.compile(r"\bi've\b", re.I), "I've"),
        (re.compile(r"\bi'd\b", re.I), "I'd"), (re.compile(r"\bi'll\b", re.I), "I'll")]

def load_glossary(p):
    out = []
    for line in pathlib.Path(p).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=>" not in line: continue
        a, b = line.split("=>", 1)
        out.append((re.compile(r"\b" + re.escape(a.strip()) + r"\b", re.I), b.strip()))
    return out

def main():
    inp, outp = sys.argv[1], sys.argv[2]
    gl = load_glossary(sys.argv[3]) if len(sys.argv) > 3 else []
    def fix(line):
        if "-->" in line or line.strip().isdigit() or not line.strip():
            return line
        s = line
        for pat, rep in gl: s = pat.sub(rep, s)   # 專有名詞先
        for pat, rep in subs: s = pat.sub(rep, s)  # 再通用
        return s
    txt = pathlib.Path(inp).read_text(encoding="utf-8")
    pathlib.Path(outp).write_text("\n".join(fix(l) for l in txt.split("\n")), encoding="utf-8")
    print(f"潤色 -> {outp}")

if __name__ == "__main__":
    main()
