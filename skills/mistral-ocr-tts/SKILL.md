---
name: mistral-ocr-tts
description: Use Mistral AI's API to (1) OCR documents and images into clean Markdown, and (2) generate English speech audio (TTS) from text. Trigger whenever the user wants to extract text from a PDF, scanned document, photo, or image — especially batches of files or when they want the result as Markdown/structured text — or says things like "OCR this", "把這份PDF/掃描檔轉成文字", "extract the text from this image", "讀出這份文件存成markdown". Also trigger whenever the user wants to turn English text into spoken audio / a voiceover / an mp3, e.g. "read this out loud", "text to speech", "generate narration", "把這段英文唸成語音". OCR is multilingual and handles Chinese; TTS supports English and 8 other Western/Indic/Arabic languages but NOT Chinese or Japanese. Requires the MISTRAL_API_KEY environment variable.
---

# Mistral OCR + TTS

用 Mistral API 做兩件事：把文件/影像 OCR 成 Markdown，以及把英文文字轉成語音 mp3。

## 什麼時候用、什麼時候不用

- **OCR**：要把 PDF、掃描檔、照片、圖片裡的文字抽出來，特別是「整批多檔」或「要乾淨的 Markdown / 結構化輸出」時，用這個 skill。
  - 反例：使用者只在對話裡丟一兩張圖請你看內容，直接用你的原生讀檔能力更快，不必動用本 skill。
- **TTS**：要把**英文**文字唸成語音 / 旁白 / mp3 時用。**中文唸不了**（Mistral TTS 只支援 9 種語言，不含中文、日文）。若使用者要中文語音合成，明白告知此 skill 做不到。

## 前置：API key

腳本從環境變數 `MISTRAL_API_KEY` 讀 key。若未設定，腳本會直接報錯並提示設定方式：

```powershell
setx MISTRAL_API_KEY "你的key"
```

設定後要重開終端機 / 重啟 Claude Code 才生效。

## 怎麼執行

本 skill 自帶獨立 venv，**一律用它的絕對路徑 python 跑**，不要用系統 python（避免使用者當下啟用的專案 venv 沒裝 mistralai）：

```
C:\Users\stans\.claude\skills\mistral-ocr-tts\.venv\Scripts\python.exe
```

腳本在 `scripts/` 底下。下面範例用 `PY` 代表上面那個 python 路徑。

### OCR：文件/影像 → Markdown

```bash
# 印到畫面
PY scripts/ocr.py "C:\path\to\scan.pdf"

# 寫成 .md 檔
PY scripts/ocr.py "C:\path\to\scan.pdf" -o result.md

# 也吃 URL 與圖片
PY scripts/ocr.py "https://example.com/doc.pdf" -o doc.md
PY scripts/ocr.py "C:\path\to\photo.jpg"
```

- 吃 PDF 與常見影像格式（png/jpg/jpeg/webp/gif/bmp/tiff），本機路徑或 http(s) URL 皆可。
- 多頁文件每頁之間用 `---` 分隔。
- 預設模型 `mistral-ocr-latest`；要鎖版本可加 `--model mistral-ocr-2512`。
- 批次處理就對每個檔案各跑一次（用迴圈），輸出各自的 `.md`。

### TTS：英文文字 → mp3

```bash
# 直接給文字
PY scripts/tts.py "Hello, this is a test." -o hello.mp3

# 從文字檔讀
PY scripts/tts.py -f script.txt -o narration.mp3

# 指定音色（用 slug 或名稱片段）
PY scripts/tts.py "Good morning" -o gm.mp3 --voice en_paul_sad

# 列出所有可用音色
PY scripts/tts.py --list-voices
```

- 不指定 `--voice` 時自動挑第一個英文音色。
- 不指定 `-o` 時預設輸出 `tts_output.mp3`。
- 內容請用英文；丟中文進去結果不會正確。

## 費用概念（提醒使用者用）

- OCR 約每 1000 頁數美元（最新代標準價約 $4，Batch 約 $2）。
- TTS 按字元計，約每 1000 字元 $0.016。
- 量大時先估一下頁數/字元數再跑。
