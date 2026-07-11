#!/usr/bin/env bash
# burn.sh <video> <srt> <out.mp4> — 燒字幕（小字號、貼底、白字黑邊）。
# env：SUB_FONTSIZE（預設 16，libass 相對 PlayResY，大檔用小數字）、SUB_FONT（字體名，預設 Arial）。
set -euo pipefail
VIDEO="$1"; SRT="$2"; OUT="$3"
FS="${SUB_FONTSIZE:-16}"
FN="${SUB_FONT:-Arial}"
# subtitles filter 的路徑要轉義 Windows 磁碟冒號
ESRT="$(printf '%s' "$SRT" | sed 's/\\/\//g; s/:/\\:/g')"
STYLE="FontName=${FN},Fontsize=${FS},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=28"
ffmpeg -y -i "$VIDEO" -vf "subtitles='${ESRT}':force_style='${STYLE}'" \
  -c:v libx264 -preset veryfast -crf 21 -pix_fmt yuv420p -r 30 -c:a copy "$OUT" -loglevel error
echo "OUT=$OUT" >&2
