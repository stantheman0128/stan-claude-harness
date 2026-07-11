#!/usr/bin/env python3
"""make_srt.py <video> <out.srt> [lang] — Groq 詞級時間戳 → 斷行 SRT（demo 影片跟讀字幕）。
lang 預設 en；中英混用或非英文請傳 zh / auto（不傳而念中文會被靜默誤轉成英文）。
需求：ffmpeg + Groq 金鑰（~/.groq_key 或環境變數 GROQ_API_KEY）。
詞級不可用時自動退回 segment 級硬切。"""
import sys, os, json, subprocess, pathlib, urllib.request, urllib.error

def key():
    k = os.environ.get("GROQ_API_KEY")
    if k: return k.strip()
    return (pathlib.Path.home() / ".groq_key").read_text(encoding="utf-8").strip()

def ts(s):
    h=int(s//3600); m=int(s%3600//60); sec=int(s%60); ms=int(round((s-int(s))*1000))
    if ms==1000: sec+=1; ms=0
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

def main():
    video, out_srt = sys.argv[1], sys.argv[2]
    lang = sys.argv[3] if len(sys.argv) > 3 else "en"
    mp3 = video + ".sub.16k.mp3"
    subprocess.run(["ffmpeg","-y","-i",video,"-ar","16000","-ac","1","-b:a","48k",mp3,"-loglevel","error"], check=True)
    boundary = "----srtBOUND7Q1Z"
    fields = [("model","whisper-large-v3-turbo"),("response_format","verbose_json"),
              ("timestamp_granularities[]","word"),("timestamp_granularities[]","segment"),("language",lang)]
    body = b""
    for k,v in fields:
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    data = open(mp3,"rb").read()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\n'
             f'Content-Type: audio/mpeg\r\n\r\n').encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request("https://api.groq.com/openai/v1/audio/transcriptions", data=body,
        headers={"Authorization": f"Bearer {key()}", "User-Agent": "Mozilla/5.0",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        j = json.loads(urllib.request.urlopen(req, timeout=600).read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Groq 錯誤 {e.code}: {e.read().decode()[:400]}")
    words = j.get("words", []) or []
    print(f"  {len(words)} 詞級時間戳")

    lines = []
    if words:
        MAXC, MAXD, MAXGAP = 44, 3.4, 0.6
        cur = []
        def flush():
            if cur:
                lines.append((cur[0]["start"], cur[-1]["end"], " ".join(w["word"].strip() for w in cur).strip()))
                cur.clear()
        for w in words:
            if cur:
                t = " ".join(x["word"].strip() for x in cur)
                end_punct = cur[-1]["word"].strip()[-1:] in ".!?"
                if (len(t)+1+len(w["word"].strip())>MAXC or w["start"]-cur[-1]["end"]>MAXGAP
                        or w["end"]-cur[0]["start"]>MAXD or end_punct):
                    flush()
            cur.append(w)
        flush()
    else:
        for s in j.get("segments", []):
            st,en,txt = s["start"],s["end"],s["text"].strip(); wds=txt.split()
            pieces=[]; chunk=[]; c=0
            for wd in wds:
                if c+len(wd)+1>44 and chunk: pieces.append(" ".join(chunk)); chunk=[]; c=0
                chunk.append(wd); c+=len(wd)+1
            if chunk: pieces.append(" ".join(chunk))
            n=len(pieces) or 1
            for i,p in enumerate(pieces):
                lines.append((st+(en-st)*i/n, st+(en-st)*(i+1)/n, p))

    buf=[]
    for i,(st,en,txt) in enumerate(lines,1):
        if en<=st: en=st+0.6
        buf.append(f"{i}\n{ts(st)} --> {ts(en)}\n{txt}\n")
    pathlib.Path(out_srt).write_text("\n".join(buf), encoding="utf-8")
    print(f"  {len(lines)} 行 -> {out_srt}")

if __name__ == "__main__":
    main()
