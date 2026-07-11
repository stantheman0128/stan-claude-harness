---
name: mineru
description: 把 PDF 或文件（DOCX/PPTX/圖片）在本機解析成乾淨 Markdown/JSON，特別強在「複雜技術文件」——數學公式轉 LaTeX、複雜/跨頁表格轉 HTML、多欄與正確閱讀順序、掃描檔 OCR（109 語含繁簡中文）。免 API、免費、資料留本機。觸發詞：「把這份 PDF/論文/報告轉成 markdown」「抽出公式/表格」「technical PDF to markdown」「parse this PDF locally」。要快、雲端、單張圖 OCR 或英文 TTS 改用 mistral-ocr-tts。
user-invocable: true
---

# MinerU — 本機技術文件解析（PDF→Markdown）

把版面複雜的 PDF（尤其含**公式、表格、多欄、掃描**）在本機轉成 LLM-ready 的 Markdown/JSON。OpenDataLab 出品，開源免費，資料不外流。

## 什麼時候用這個 vs mistral-ocr-tts

| 情況 | 用 |
|---|---|
| 含數學公式（要 LaTeX）、複雜/跨頁表格、多欄論文、長技術文件、要離線/不上雲/批次 | **mineru（本機）** |
| 隨手 OCR 一張圖、短檔、要快又懶得等、要英文 TTS | `mistral-ocr-tts`（雲端 API） |

注意：DOCX/PPTX/XLSX 輸入走**零模型的純 Python office backend**——CPU 也快，「mineru 慢」的分流理由只適用 PDF/掃描檔，office 文件不必讓給雲端。（2026-07-10 重評核實）

## 環境（已裝好，別重裝）

- 專屬 venv：`~/.claude/skills/mineru/.venv`（CPython 3.12；系統的 3.13 在 Windows 跑不動 MinerU）。
- 後端：**pipeline（純 CPU）**。這台是 GTX 1060（Pascal），用不到 GPU 加速，所以**會慢**——多頁 PDF 可能要幾分鐘，正常現象。
- 模型：第一次執行會自動下載（幾 GB，存進快取），之後沿用。來源用 HuggingFace。
- 注意：`mineru[pipeline]` 漏了一個傳遞依賴 `six`（pytorchocr OCR operator 要用），已手動補裝。若哪天重建 venv，記得 `uv pip install six`。

## 怎麼跑

最省事：用 wrapper（會帶好 venv、模型來源、CPU backend）：

```bash
bash ~/.claude/skills/mineru/scripts/run.sh <輸入.pdf> [輸出目錄]
```

或直接呼叫 CLI（同效果）：

```bash
MINERU_MODEL_SOURCE=huggingface \
  ~/.claude/skills/mineru/.venv/Scripts/mineru.exe -p <輸入.pdf> -o <輸出目錄> -b pipeline
```

常用旗標：
- `-b pipeline`：固定用 CPU 後端（這台必用，別用 vlm/vllm，裝的時候就沒裝）。
- `-l ch`：中文文件指定語言可提升 OCR（`ch` 簡中模型對繁中也通用；英文 `en`）。
- `-p` 可給單檔或整個資料夾；`-o` 是輸出根目錄。

環境變數小抄（3.4.x 程式碼核實有效）：
- `MINERU_FORMULA_CH_SUPPORT=1`：中文公式實驗性支援
- `MINERU_TABLE_MERGE_ENABLE=0`：關跨頁表格合併（表格被錯併時用）
- `MINERU_PDF_RENDER_TIMEOUT=<秒>`：異常 PDF 防卡
- `MINERU_INTRA_OP_NUM_THREADS=<N>`：CPU 併發調節

## 輸出在哪

PDF 輸入在 `<輸出目錄>/<檔名>/auto/`；**DOCX/PPTX/XLSX 輸入在 `<檔名>/office/`**（不是 auto/）。底下：
- `<檔名>.md`：主結果（公式為 LaTeX、表格為 HTML、含圖）。
- `<檔名>_content_list.json`：依閱讀順序的結構化內容。
- `images/`：抽出的圖。
- `*_layout.pdf` / `*_span.pdf`：版面/區塊視覺化（debug 用）。

## 限制 / 注意

- CPU 模式慢；別拿它做「隨手快轉」，那種用 mistral。
- 首跑要等模型下載。
- 只裝了 `pipeline` extra（無 vllm/lmdeploy，Windows CPU 正解）；若哪天換了 Volta 以上的新卡才值得加 `vlm`。
- 授權精確名稱是 **MinerU Open Source License**（Apache 2.0＋附加條款：月活破 1 億或月營收破 2000 萬美元須商業授權、線上服務須標示使用 MinerU）——個人使用零影響，但引用時別寫成純 Apache。
