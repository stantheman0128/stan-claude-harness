#!/usr/bin/env python3
"""verify_cuts.py <cut_video> <manifest.tsv> [lang] — 自動偵測接縫「半句切斷」。
讀 cut.sh 產出的 manifest（各段在成品中的起訖），把成品重新轉錄（Groq segment 級，
segment 邊界 ≈ 句子），對每個接縫檢查：
  - 前段是講話段（narr/keep）：接縫前最後一句是否以句末標點收尾 → 否則 SUSPECT（話沒說完就切）
  - 後段是講話段：接縫後第一句是否小寫字母開頭（僅英文）→ 是則 SUSPECT（半句開頭）
輸出每接縫 OK/SUSPECT + 前後文；有任何 SUSPECT 時 exit code 1。
這是啟發式：SUSPECT = 必人工覆核；OK 也建議抽查開頭與結尾兩處。
lang 預設 en；中文/混講傳 zh 或 auto（zh 無大小寫，只驗前段標點）。"""
import sys, os, json, subprocess, pathlib, urllib.request, urllib.error

END_PUNCT = tuple('.!?。！？…"\')')
SPEECH = {"narr", "keep"}

def groq_key():
    k = os.environ.get("GROQ_API_KEY")
    if k: return k.strip()
    return (pathlib.Path.home() / ".groq_key").read_text(encoding="utf-8").strip()

def transcribe(video, lang):
    """回傳詞級時間戳 [(start,end,word)]。拼接+變速過的音訊上 segment 邊界不可靠
    （Groq 會把跨接縫內容併成大 segment），詞級才準——判定與引文都必須用詞級。"""
    mp3 = video + ".vfy.16k.mp3"
    subprocess.run(["ffmpeg","-y","-i",video,"-ar","16000","-ac","1","-b:a","48k",mp3,"-loglevel","error"], check=True)
    boundary = "----vfyBOUND7Q1Z"
    fields = [("model","whisper-large-v3-turbo"),("response_format","verbose_json"),
              ("timestamp_granularities[]","word"),("timestamp_granularities[]","segment")]
    if lang != "auto": fields.append(("language", lang))
    body = b""
    for k,v in fields:
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\n'
             f'Content-Type: audio/mpeg\r\n\r\n').encode() + open(mp3,"rb").read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request("https://api.groq.com/openai/v1/audio/transcriptions", data=body,
        headers={"Authorization": f"Bearer {groq_key()}", "User-Agent": "Mozilla/5.0",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        j = json.loads(urllib.request.urlopen(req, timeout=600).read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Groq 錯誤 {e.code}: {e.read().decode()[:400]}")
    finally:
        try: os.remove(mp3)
        except OSError: pass
    return [(w["start"], w["end"], w["word"].strip()) for w in j.get("words", []) if w["word"].strip()]

def main():
    video, manifest = sys.argv[1], sys.argv[2]
    lang = sys.argv[3] if len(sys.argv) > 3 else "en"
    rows = []
    for ln in pathlib.Path(manifest).read_text(encoding="utf-8").splitlines()[1:]:
        c = ln.split("\t")
        if len(c) >= 7: rows.append({"type": c[1], "ss": c[2], "end": float(c[6])})
    words = transcribe(video, lang)
    if not words:
        sys.exit("拿不到詞級時間戳，無法可靠驗接縫（segment 級在拼接音訊上會漂移）")
    print(f"轉錄 {len(words)} 詞，檢查 {max(len(rows)-1,0)} 個接縫：")
    suspects = 0
    for a, b in zip(rows, rows[1:]):
        T = a["end"]
        msgs = []
        before = [w for w in words if w[1] <= T + 0.2]
        after = [w for w in words if w[0] >= T - 0.2 and w not in before]
        if a["type"] in SPEECH and before:
            lastw = before[-1]
            ctx = " ".join(w[2] for w in before[-8:])
            # 接縫前最後一個詞貼著切點、且句子還「開著」→ 疑似話沒說完
            if not lastw[2].endswith(END_PUNCT) and T - lastw[1] < 1.2:
                msgs.append(f"前段疑未講完: …{ctx!r}")
        if b["type"] in SPEECH and lang == "en" and after:
            firstw = after[0][2]
            if firstw and firstw[0].islower():
                msgs.append(f"後段疑半句開頭: {' '.join(w[2] for w in after[:8])!r}…")
        tag = "SUSPECT" if msgs else "OK"
        if msgs: suspects += 1
        print(f"  [{tag}] {a['type']}→{b['type']} @ {T:.1f}s" + ("".join("\n          " + m for m in msgs)))
    print(f"\n結果：{suspects} 個 SUSPECT" + ("（必逐一人工覆核，確認是否要調 EDL 重剪）" if suspects else "（仍建議抽查開頭與結尾）"))
    sys.exit(1 if suspects else 0)

if __name__ == "__main__":
    main()
