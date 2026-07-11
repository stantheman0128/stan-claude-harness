---
name: transcribe
description: Use when Stan wants to transcribe a YouTube video or audio file into a clean Traditional-Chinese transcript. Triggers on "幫我轉錄", "轉逐字稿", "transcribe this video", "幫我把這支影片轉成文字", "我要 transcribe", or a YouTube URL given with transcribe intent. Runs the proven pipeline: yt-dlp 高音質音訊 → Groq Whisper large-v3-turbo → Claude 約束式後校正。
---

# Transcribe Pipeline（Stan 專用，已實測）

Stan 說「我要 transcribe 這支影片 / 幫我轉錄」時，自動執行以下流程，**不要再逐項問他**。環境已全部備好（deno、yt-dlp 設定檔、Groq 金鑰）。

## 環境前提（都已就緒，無需重裝）
- 工具：`~/Downloads/video-lens/vtranscribe.py`（支援 groq / sensevoice / whisper 後端）
- Groq 金鑰：`~/.groq_key`（讀取自動）
- deno 在 PATH（新終端機自動帶；若 yt-dlp 退回 format 18，先 `deno --version` 確認）。本工作目錄下若 deno 不在 PATH，export：`/c/Users/stans/AppData/Local/Microsoft/WinGet/Packages/DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe`
- yt-dlp 設定檔已啟用 `--remote-components ejs:github`（自動拿高音質音訊）

## 步驟

### 1. 先看有沒有字幕（有就免 ASR、最省）
```bash
python3 -m yt_dlp --list-subs "<URL>" 2>/dev/null | grep -iE "zh|en" | head
```
若有 zh/en 字幕軌：直接抓字幕轉 srt，跳過 ASR：
```bash
python3 -m yt_dlp --skip-download --write-subs --write-auto-subs --sub-langs "zh.*,en.*" --convert-subs srt -o "%(id)s.%(ext)s" "<URL>"
```

### 2. 字幕被禁用 → 跑 ASR pipeline（主力）
```bash
python3 ~/Downloads/video-lens/vtranscribe.py "<URL或本地音檔>" --backend groq --lang auto
```
- 語言旗標：純中文 `--lang zh`、純英文 `--lang en`、中英混雜 `--lang auto`
- 離線/不想用雲端：改 `--backend sensevoice`（中文，本地免費、15秒/12分）；純英文離線改 `--backend whisper`
- 工具會**自動爬影片 metadata**（標題/頻道/章節/描述）寫進 raw.txt 開頭的「影片資訊」區塊，並對 **>25MB（約 70 分鐘以上）的長影片自動切 10 分鐘段**——你不用處理。
- 產出：`~/Downloads/video-lens/audio/<id>.groq.raw.txt`

### 3. 讀 raw 檔，做「約束式後校正」（關鍵品質步驟，由你 Claude 親自做）
**先讀 raw.txt 開頭的「影片資訊」區塊**（標題/頻道/章節/描述）當 context 與**種子詞表**。創作者的描述常含親寫的開頭或關鍵專名，可直接拿來訂正（例：描述寫「賭注」就知道 raw 的「毒度」要改成「賭注」；標題有 SpaceX 就確認專名）。

校正規則：
- **整篇當語意背景**，只修「明顯辨識錯誤」：同音/近音錯字、英文專名糊掉（spaceac→SpaceX、Gorak→Grok）、數字格式、標點。
- **種子詞表來自 metadata**（標題/描述/章節），再依主題擴充：SpaceX, Starlink, Grok, Anthropic, Tesla, Colossus, 輝達, xAI, 估值, 招股書, 本益比…
- **詞表跨段累積（長影片切段時關鍵）**：逐段校正，把前段已確認的專名（如第 1 段定下的 Anthropic）累積進詞表往後傳，確保整片專名前後一致，**不要每段重猜**。
- **不確定保持原樣**，不臆測；不得改寫語氣、新增/刪除/重排句子、腦補內容。某段「改後 vs 原文」差異過大 → 退回原文，防過度改寫。
- 輸出**繁體中文**（Stan 鐵則，禁簡體；小心形近字 [[feedback_chinese_character_precision]]）。

### 4. 存檔並回報
存成 `<id>.clean.txt`（或依 Stan 指定）。回報：來源、用了字幕還是 ASR、成本（Groq turbo $0.04/hr）、成品位置。

## 模型/成本備註
- Groq 只有 2 個 ASR：`whisper-large-v3-turbo`（$0.04/hr，現用，最佳 CP）、`whisper-large-v3`（$0.111/hr，略準）。Stan 的優先序是速度>價格>準度 + 後校正，**turbo 為最佳**。要更準改 `--model`（whisper 本地後端）或之後支援 large-v3。
- 若 Groq 回 403/error 1010 → Cloudflare 擋 UA，工具已內建瀏覽器 User-Agent，無需處理。

## 可選後續
轉完若 Stan 要「統整成文章」，再依 [[feedback_video_to_threads]] / 一般文章流程處理；本 skill 只負責產出乾淨逐字稿。相關：[[howto_youtube_asr_pipeline]]。
