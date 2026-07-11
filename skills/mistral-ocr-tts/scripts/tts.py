"""Mistral TTS：把英文文字轉成語音 mp3。

注意：Mistral TTS 不支援中文。支援英、法、德、西、荷、葡、義、印地、阿拉伯共 9 種。

用法：
    python tts.py "Hello world" -o hello.mp3
    python tts.py -f speech.txt -o out.mp3 --voice en_paul_sad
    python tts.py --list-voices
"""
import argparse
import base64
import sys

from _client import get_client

DEFAULT_MODEL = "voxtral-mini-tts-latest"


def pick_voice(client, wanted):
    voices = client.audio.voices.list(limit=100).items
    if wanted:
        for v in voices:
            if wanted == v.id or wanted == v.slug or wanted.lower() in (v.name or "").lower():
                return v
        sys.exit(f"找不到音色：{wanted}（用 --list-voices 看清單）")
    # 預設挑第一個英文音色
    for v in voices:
        if any(str(l).startswith("en") for l in (v.languages or [])):
            return v
    return voices[0]


def main():
    ap = argparse.ArgumentParser(description="Mistral TTS -> mp3（英文）")
    ap.add_argument("text", nargs="?", help="要唸的英文文字")
    ap.add_argument("-f", "--file", help="改從文字檔讀入內容")
    ap.add_argument("-o", "--output", default="tts_output.mp3", help="輸出 mp3 路徑")
    ap.add_argument("--voice", help="音色 id / slug / 名稱片段；省略用第一個英文音色")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--list-voices", action="store_true", help="列出可用音色後結束")
    args = ap.parse_args()

    client = get_client()

    if args.list_voices:
        for v in client.audio.voices.list(limit=100).items:
            langs = ",".join(v.languages or [])
            print(f"{v.slug:24} {langs:10} {v.gender or '':6} {v.name}")
        return

    if args.file:
        text = open(args.file, encoding="utf-8").read()
    elif args.text:
        text = args.text
    else:
        sys.exit("請給要唸的文字（直接當參數）或用 -f 指定文字檔。")

    voice = pick_voice(client, args.voice)
    resp = client.audio.speech.complete(
        model=args.model, input=text, voice_id=voice.id, response_format="mp3",
    )
    audio = resp.audio_data
    if isinstance(audio, str):
        audio = base64.b64decode(audio)
    with open(args.output, "wb") as f:
        f.write(audio)
    print(f"TTS 完成（音色 {voice.slug}）-> {args.output}（{len(audio):,} bytes）")


if __name__ == "__main__":
    main()
