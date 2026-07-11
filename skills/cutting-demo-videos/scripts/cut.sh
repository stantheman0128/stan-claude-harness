#!/usr/bin/env bash
# cut.sh <video> <edl.txt> <out.mp4>
# 把 demo 錄影按 EDL 剪成精華短片。EDL 每行（`#` 起頭或行內 `#` 之後皆為註解）：
#   narr  <ss> <len> [speed]    講解段：去靜音 + 提速(預設1.15) + 音量拉平 + 接縫微淡化
#   trans <ss> <len> [factor]   過場：加速(預設8) + 靜音 + 小標(淡入後輕脈動) + 淡入淡出 + 暗角
#   keep  <ss> <len> [speed]    原樣保留(可提速,預設1.0) + 音量拉平 + 接縫微淡化
#   card  <dur> <text...>       黑底置中標題卡(淡入淡出;文字避免 : ' # \ 特殊字元)
# ss/len 為來源影片秒數。行序 = 成品順序。
# 產出 <out>.manifest.tsv（每段在成品中的起訖，給 verify_cuts.py 驗接縫用）。
# env：
#   TRANS_LABEL   過場小標文字（預設 '>> fast forward >>'）
#   DEMO_FONT     drawtext 字體檔
#   DRAFT=1       低品質快速預覽（ultrafast/crf30，迭代 EDL 用）
#   SOFT_CUTS=1   段間 0.12s 黑場軟切（預設硬切）
#   CUT_CACHE     段落快取目錄（預設 <out 同層>/.cutcache；改 EDL 只重跑變動段）
# 需求：ffmpeg、auto-editor 在 PATH（Windows 見 SKILL.md 的 PATH 提醒）。
set -euo pipefail
VIDEO="$1"; EDL="$2"; OUT="$3"
CACHE="${CUT_CACHE:-$(dirname "$OUT")/.cutcache}"; mkdir -p "$CACHE"
TMP="$CACHE/tmp.$$"; trap 'rm -f "$TMP".*' EXIT

DRAFT="${DRAFT:-0}"
if [ "$DRAFT" = "1" ]; then
  VENC=(-c:v libx264 -preset ultrafast -crf 30 -pix_fmt yuv420p -r 30 -video_track_timescale 90000)
else
  VENC=(-c:v libx264 -preset veryfast -crf 21 -pix_fmt yuv420p -r 30 -video_track_timescale 90000)
fi
AENC=(-c:a aac -ar 48000 -ac 2 -b:a 128k)
LOUD="loudnorm=I=-16:TP=-1.5:LRA=11"   # 各段音量拉到同一標準
FONT="${DEMO_FONT:-C\\:/Windows/Fonts/arialbd.ttf}"
LABEL="${TRANS_LABEL:->> fast forward >>}"
SOFT="${SOFT_CUTS:-0}"
read -r W H < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$VIDEO" | tr ',' ' ')
VSIG="$(stat -c '%Y_%s' "$VIDEO" 2>/dev/null || echo 0)"

dur(){ ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 "$1"; }
key(){ printf '%s' "$*" | md5sum | cut -d' ' -f1; }
fnum(){ awk "BEGIN{printf \"%.3f\", $1}"; }

# 接縫微淡化（15ms 防爆音）；SOFT_CUTS 時再加視訊黑場軟切
polish_edges(){ # in out
  local d; d=$(dur "$1")
  local af="afade=t=in:st=0:d=0.015,afade=t=out:st=$(fnum "$d-0.015"):d=0.015"
  if [ "$SOFT" = "1" ]; then
    ffmpeg -y -i "$1" -vf "fade=t=in:st=0:d=0.12,fade=t=out:st=$(fnum "$d-0.12"):d=0.12" -af "$af" "${VENC[@]}" "${AENC[@]}" "$2" -loglevel error
  else
    ffmpeg -y -i "$1" -c:v copy -af "$af" "${AENC[@]}" "$2" -loglevel error   # 只重編音訊，視訊直拷
  fi
}

gen_speech(){ # type ss len speed seg
  local type=$1 ss=$2 len=$3 sp=$4 seg=$5
  ffmpeg -y -ss "$ss" -i "$VIDEO" -t "$len" "${VENC[@]}" "${AENC[@]}" "$TMP.raw.mp4" -loglevel error
  if [ "$type" = narr ]; then
    auto-editor "$TMP.raw.mp4" --margin 0.2s -o "$TMP.tight.mp4" --no-open >/dev/null 2>&1
  else mv "$TMP.raw.mp4" "$TMP.tight.mp4"; fi
  if [ "$sp" = "1.0" ] || [ "$sp" = "1" ]; then
    ffmpeg -y -i "$TMP.tight.mp4" -c:v copy -af "$LOUD" "${AENC[@]}" "$TMP.sp.mp4" -loglevel error
  else
    ffmpeg -y -i "$TMP.tight.mp4" -filter:v "setpts=PTS/${sp}" -filter:a "atempo=${sp},${LOUD}" "${VENC[@]}" "${AENC[@]}" "$TMP.sp.mp4" -loglevel error
  fi
  polish_edges "$TMP.sp.mp4" "$seg"
}

gen_trans(){ # ss len factor seg
  local ss=$1 len=$2 f=$3 seg=$4
  local td; td=$(fnum "$2/$3")
  local DT="drawtext=fontfile='${FONT}':text='${LABEL}':fontsize=56:fontcolor=white:borderw=3:bordercolor=black@0.85:x=(w-tw)/2:y=h-190:box=1:boxcolor=black@0.55:boxborderw=26:alpha='if(lt(t\\,0.4)\\,t/0.4\\,0.78+0.22*sin(2*PI*(t-0.4)*1.5))'"
  local VF="setpts=PTS/${f},vignette=PI/6,${DT},fade=t=in:st=0:d=0.3"
  awk "BEGIN{exit !($td>0.7)}" && VF="$VF,fade=t=out:st=$(fnum "$td-0.3"):d=0.3"
  # -t 在 -i 前 = 限制讀取範圍（放後面會讀到片尾，setpts 把整段拉進來）
  ffmpeg -y -ss "$ss" -t "$len" -i "$VIDEO" -filter:v "$VF" -an "${VENC[@]}" "$TMP.tv.mp4" -loglevel error
  local d; d=$(dur "$TMP.tv.mp4")
  ffmpeg -y -i "$TMP.tv.mp4" -f lavfi -t "$d" -i anullsrc=r=48000:cl=stereo -map 0:v -map 1:a "${VENC[@]}" "${AENC[@]}" -shortest "$seg" -loglevel error
}

gen_card(){ # dur text seg
  local d=$1 text=$2 seg=$3
  local DT="drawtext=fontfile='${FONT}':text='${text}':fontsize=72:fontcolor=white:x=(w-tw)/2:y=(h-th)/2"
  ffmpeg -y -f lavfi -i "color=c=0x0f1216:s=${W}x${H}:r=30" -f lavfi -i anullsrc=r=48000:cl=stereo \
    -t "$d" -vf "${DT},fade=t=in:st=0:d=0.4,fade=t=out:st=$(fnum "$d-0.4"):d=0.4" \
    -map 0:v -map 1:a "${VENC[@]}" "${AENC[@]}" -shortest "$seg" -loglevel error
}

MAN="$OUT.manifest.tsv"; printf 'idx\ttype\tss\tlen\tsegdur\tout_start\tout_end\n' > "$MAN"
i=0; acc=0; order=()
while IFS= read -r line || [ -n "$line" ]; do
  line="${line%%#*}"                     # 剝行內註解（否則註解被當成 factor）
  read -r type rest <<<"$line" || true
  [ -z "${type:-}" ] && { type=""; continue; }
  i=$((i+1))
  case "$type" in
    narr|keep)
      read -r ss len factor _ <<<"$rest"
      if [ "$type" = narr ]; then sp="${factor:-1.15}"; else sp="${factor:-1.0}"; fi
      h=$(key "v1|$type|$ss|$len|$sp|$SOFT|$DRAFT|$VSIG"); seg="$CACHE/$h.mp4"
      [ -f "$seg" ] && echo "  [cache] $type ss=$ss len=$len" >&2 || gen_speech "$type" "$ss" "$len" "$sp" "$seg"
      ;;
    trans)
      read -r ss len factor _ <<<"$rest"; f="${factor:-8}"
      h=$(key "v1|trans|$ss|$len|$f|$LABEL|$DRAFT|$VSIG"); seg="$CACHE/$h.mp4"
      [ -f "$seg" ] && echo "  [cache] trans ss=$ss len=$len" >&2 || gen_trans "$ss" "$len" "$f" "$seg"
      ;;
    card)
      read -r len text <<<"$rest"; ss=-
      h=$(key "v1|card|$len|$text|$DRAFT|$W|$H"); seg="$CACHE/$h.mp4"
      [ -f "$seg" ] && echo "  [cache] card" >&2 || gen_card "$len" "$text" "$seg"
      ;;
    *) echo "未知 EDL type: $type" >&2; exit 1;;
  esac
  order+=("$seg")
  sd=$(dur "$seg"); end=$(fnum "$acc+$sd")
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$i" "$type" "$ss" "${len:-}" "$sd" "$acc" "$end" >> "$MAN"
  printf '  %-6s ss=%s len=%s -> %ss (成品 %s-%s)\n' "$type" "$ss" "${len:-}" "$sd" "$acc" "$end" >&2
  acc=$end; type=""
done < "$EDL"

LIST="$TMP.list.txt"; : > "$LIST"
for s in "${order[@]}"; do echo "file '$s'" >> "$LIST"; done
if ! ffmpeg -y -f concat -safe 0 -i "$LIST" -c copy "$OUT" -loglevel error 2>/dev/null; then
  echo "  -c copy 失敗，改 filter concat 重編碼（常見、非錯誤）" >&2
  args=(); fc=""; j=0
  for s in "${order[@]}"; do args+=(-i "$s"); fc+="[$j:v][$j:a]"; j=$((j+1)); done
  fc+="concat=n=${j}:v=1:a=1[v][a]"
  ffmpeg -y "${args[@]}" -filter_complex "$fc" -map "[v]" -map "[a]" "${VENC[@]}" "${AENC[@]}" "$OUT" -loglevel error
fi
echo "OUT=$OUT total=$(dur "$OUT")s manifest=$MAN" >&2
