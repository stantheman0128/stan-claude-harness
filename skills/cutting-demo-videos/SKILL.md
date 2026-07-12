---
name: cutting-demo-videos
description: Use when condensing a long screen-recording demo that has voiceover into a short highlight cut - stripping dead air and speech pauses, speeding up idle or gameplay stretches into labeled fast-forward transitions, and burning in word-level subtitles. Triggers on 壓短 demo 影片, 剪掉空白/停頓, 加速這段遊玩, 去蕪存菁 影片, demo 影片剪輯, condensing a talking screen capture, "screen recording is too long".
---

# Cutting Demo Videos

## Overview
Turn a long talking screen-demo (app/tool walkthrough with voiceover) into a tight highlight reel: remove speech pauses, fast-forward idle stretches as labeled transitions, burn subtitles. The scripts do the mechanics; the judgment below is what makes the cut *good*. Runs fine on a smaller model once the EDL is set — the taste lives in the EDL and the principles.

## Pipeline
1. **Ask deliverables upfront — before touching the video.** Ask the user (AskUserQuestion if available, else in chat) which caption deliverables they want. This only affects steps 6+ (nothing about cutting changes), but asking now — not after the burned video is already delivered — avoids a second pass:
   - **None** — skip step 6 entirely.
   - **Burned-in only** — captions baked into the pixels. For portfolio pages, X/Twitter, anywhere without a native CC toggle.
   - **Standalone SRT only** — deliver the clean (unburned) cut + a `.srt`. For platforms with native caption upload — **this is what YouTube's own CC slot wants**: viewers can toggle/translate/search it, which burned-in text can't do.
   - **Both** — burned video (portfolio/social) AND clean video + `.srt` (YouTube). Three output files.
2. **Understand** — transcribe the audio WITH timestamps + pull a contact sheet to locate narration vs idle stretches.
   `python <video-lens>/vtranscribe.py <video> --backend groq --lang auto`
   `ffmpeg -ss <start> -t <dur> -i <video> -vf "fps=25/<dur>,scale=440:-1,tile=5x5" -frames:v 1 sheet.jpg` (Read the jpg — one glance shows the structure.)
   **Only cutting a sub-range of a long source?** Add `-ss <start> -t <dur>` when extracting audio / building the sheet, so the transcript and the 25 tiles concentrate on the range you care about — not 15 tiles wasted on footage you'll discard.
3. **Design an EDL** — decide which spans to keep, cut, or speed up. Write `edl.txt` (format below). This is where the taste goes.
4. **Cut** — `bash scripts/cut.sh <video> edl.txt out_nosub.mp4` — precise trim → auto-editor de-silence → 1.15x + loudness-normalize + click-proof edge fades → transition speed-up + pulsing label → concat. Also writes `out_nosub.mp4.manifest.tsv` (where each segment landed in the output). Iterating on the EDL? Segments are cached — only changed lines re-render. Set `DRAFT=1` for a fast low-quality preview while tuning.
5. **Verify cut points NOW — before subtitles** — `python scripts/verify_cuts.py out_nosub.mp4 out_nosub.mp4.manifest.tsv [lang]` auto-flags splices where a sentence was likely cut mid-thought. **Every SUSPECT must be human-reviewed** (read the printed context vs the source transcript at that spot — ASR sometimes drops a leading "And"/"So", which triggers a lowercase-start false alarm; the source transcript settles it). OK splices still deserve a spot-check of the opening and the ending. Tuned for recall: a false SUSPECT costs one glance, a missed half-sentence ships broken. Half-sentence confirmed? Fix the EDL ss/len, re-run step 4 (cache makes this cheap), verify again. **Loop until clean BEFORE step 6** — burning subs first means redoing the whole subtitle chain after any re-cut.
6. **Subtitle (skip if step 1 = None)** — `python scripts/make_srt.py out_nosub.mp4 sub.srt [lang]` (word-level; lang default `en`, pass `zh`/`auto` for non-English or code-switched narration) → `python scripts/polish_srt.py sub.srt sub.polished.srt [glossary.txt]`. Then, per step 1's answer: **Burned-in** → `bash scripts/burn.sh out_nosub.mp4 sub.polished.srt out.mp4`, deliver `out.mp4` only. **Standalone SRT** → deliver `out_nosub.mp4` (rename to the final filename) + `sub.polished.srt` as-is, do NOT run burn.sh. **Both** → do both, deliver all three files with matching base names (e.g. `demo_burned.mp4`, `demo_clean.mp4`, `demo.srt`) so it's obvious which SRT pairs with which video.
7. **Final check** — spot-check burned frames (if any): subtitle size/position, transition label, no subs covering key UI.
8. **Independent LLM judge** — dispatch a CLEAN-CONTEXT subagent (it must not inherit this session's editing history — no sunk cost) with [references/judge.md](references/judge.md), filling in the input paths. It re-derives evidence itself (verify_cuts, own transcript, frames) and returns SHIP/FIX against the Ship checklist. Treat any FIX item as a re-cut loop, not a debate. A smaller model (Sonnet-class) is sufficient for this role.

## Editing principles (the judgment scripts can't do)
- **Hook fast** — first ~15s must land what it is + why it exists.
- **Keep peaks, cut noise** — keep feature demos, the hard technical bit, design care, an accuracy/proof ending. Cut repeated complaints (same gripe said 3x → keep once), filler ("um / where was I / so so"), emotional venting.
- **Strong ending** — finish on proof + a punch line, never mid-thought.
- **Pace** — narration de-silenced + light 1.15x. For idle/gameplay transitions, pick the factor from the TARGET REAL TIME, not a fixed multiplier: a silent fast-forward should land at ~3–8s of screen time (viewers get the idea in 3s; 15–20s of muted speed-up feels like dead air). 269s of gameplay → use ~90x, not 14x.
- **Don't cover key UI** with subtitles/labels — small font, bottom, consistent style.

## Cut-point rule (this is WHY step 5 exists)
Every cut point must land where a sentence finished. After each render, re-transcribe the OUTPUT and read it line-by-line against the source. If any line starts as a half-sentence, or trails off unfinished right before a cut, the ss/len is wrong — adjust the EDL and re-run. **A clipped closing line, or a sentence cut mid-word before a transition, is the most common and most damaging mistake — and you cannot hear it reliably, you have to read the transcript.**

## EDL format
```
# type   ss   len   [factor]
card    3    Colonist Stats Tracker     # title card: <dur> <text...> (no : ' # \ in text)
narr    0    25            # narration: de-silence + speed (factor = speed, default 1.15)
narr    46   116
trans   739  120   14      # transition: fast-forward factor + silence + label (default 8)
keep    859  56    1.0     # keep as-is, optional speed
```
ss and len are SECONDS in the SOURCE. Line order = final order. `#` starts a comment anywhere.

**Env knobs:** `TRANS_LABEL` (transition label, default `>> fast forward >>`) · `DEMO_FONT` (drawtext font file) · `DRAFT=1` (fast preview render) · `SOFT_CUTS=1` (0.12s dip-to-black between segments; default hard cuts — the screen-demo norm) · `CUT_CACHE` (segment cache dir) · `SUB_FONT`/`SUB_FONTSIZE` (burn.sh) · `MARGIN` (auto-editor silence-keep buffer, default `0.2s` — bump to `0.3s`–`0.4s` for fast continuous talking-head narration with little natural breathing room; default is fine for typical demo pacing with pauses).

**Fonts (Windows built-ins, pick by content):** product demo → `Segoe UI`; dev-tool/terminal demo → `Consolas`; playful content → `Comic Sans MS`. Set via `SUB_FONT` (subtitles, a font NAME) and `DEMO_FONT` (labels/cards, a font FILE path).

## Ship checklist (score every render before delivering)
1. Hook ≤15s states what it is + why it exists (read output transcript's first lines)
2. Zero half-sentence cuts — verify_cuts.py clean + SUSPECTs human-cleared
3. Ends on proof/punchline, never mid-thought (read last lines)
4. Duration within target ±10% (ffprobe)
5. Narration de-silenced, 1.1–1.2x
6. Each transition ≤20s real time, labeled
7. Deliverables match what was asked in step 1 (None/Burned/SRT/Both — not fewer, not extra); subtitles (if any) ≤2 lines, not covering key UI (spot-check 3 frames)
8. Proper nouns consistent (glossary + grep the SRT)
9. No clicks at splices, loudness even across segments (cut.sh handles; re-check if sourcing from multiple recordings)

## Common mistakes
- **Half-sentence cuts** → re-transcribe output, compare to source (Cut-point rule). Extend len to finish the sentence.
- **Transition ran to end of file** → in ffmpeg put `-t` BEFORE `-i` (limits the READ), not after (limits the OUTPUT, so setpts pulls in everything to EOF).
- **Subtitles look huge** → libass Fontsize is relative to PlayResY, not pixels; for 1080p+ frames use ~16, not 40.
- **De-silence too aggressive / speech jumps, or words visibly slur/merge (e.g. an ASR re-transcription mangles a word into a nonsense token, or a number/word silently drops)** → the 0.2s default margin is too tight for this recording's pacing. Set `MARGIN=0.3s` or higher and re-cut. Fast rapid-fire talking-head narration (little natural breathing room between phrases) needs more margin than a demo with pauses. Always re-transcribe and diff against source (Cut-point rule) — this failure mode shows up as content changes, not just short SUSPECTs.
- **`-c copy` concat falls back to re-encode** → common and fine, NOT an error. Transition segments pass through extra filters (vignette/drawtext/fade), so their timebase differs enough that the demuxer refuses stream-copy; cut.sh auto-falls-back to filter_complex concat (correct output, just slower). Budget render time.
- **Card text breaks the render** → drawtext chokes on `: ' # \` — keep card text plain words.
- **Stale cache after re-recording** → cache keys include the video's mtime+size, so a changed file re-renders automatically; delete `.cutcache/` to force-clear.
- **Delivered a burned video, then got asked for a plain SRT afterward** → this is why step 1 asks upfront. If it still happens: re-generate from `out_nosub.mp4` (steps 6's make_srt/polish), don't hand out an SRT whose timeline predates a later re-cut — a re-cut (step 5's loop) shifts every timestamp after the change, so a burned video and a "standalone" SRT from different cut revisions will drift out of sync.

## Requirements
ffmpeg, `pip install --user auto-editor`, and a Groq key at `~/.groq_key` for subtitles. Reuses `~/Downloads/video-lens/vtranscribe.py` for transcription.
**Windows:** `--user` installs auto-editor to `%APPDATA%\Python\PythonXXX\Scripts`, which is NOT on PATH by default. Before running cut.sh: `export PATH="$PATH:/c/Users/<you>/AppData/Roaming/Python/Python3XX/Scripts"` — otherwise cut.sh dies with an opaque "auto-editor: command not found" mid-run.
