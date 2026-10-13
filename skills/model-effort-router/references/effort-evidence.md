# Effort 曲線與實測

SKILL.md「Effort 速查」與「升階路徑」的佐證。

## 官方曲線

- 舊實測曲線（Opus 5，僅供比例參考）：FrontierBench low 25% → high 39% → xhigh 44.4% → max 43%（不再漲）。
- **Opus 5.5 官方曲線（System Card §8）**：CursorBench medium 52.5% / high 56.0% / max 57.8%，high 每題約 $4 已勝過 Fable 5.1 max 且只花其四分之一（p179）；GDPval-AA xhigh 1820 ≈ max 1846 但 output token 少 51%（p209）；AA-Briefcase xhigh 少 41% token（p210）；Terminal-Bench 4.0 xhigh 66.4 vs max 64.8「在雜訊內」（p178）；**FrontierCode 在 medium 最高（54.6），medium 以上反而下降**，因為高 effort 會改超出範圍的東西被扣分（p176）。2026-10-03 的結論是「coding 給 medium~high」；2026-10-13 Stan 改成品質優先，起點改成下方「每升一檔多拿到什麼」的判斷。
- Opus 5.5 SWE-bench Pro（Anthropic effort 文件，以 high 為基準）：medium -2.5 分、成本約 70%；low -8 分、約 1/3；xhigh +1.4 分、約 2.5 倍。
- 「先低檔跑、失敗的再用高檔重跑」比全部高檔便宜：Opus 先 low、失敗題重跑 high 約 97% / $0.17，全部 high 是 95.3% / $0.29。每解出一題的成本：Opus 5.5 medium 92.8% / $0.22，Fable 5.1 預設 92.3% / $1.19。
- Haiku 5.5 GDPval-AA：max 1620、medium 1277（medium 只用 max 約 1/10 的 output token）。
- Sonnet 5.5 System Card 的 effort 細節在 `model-picks.md`。

## 四模型五檔（2026-10-13 收集）

Anthropic 沒用文字公布 Sonnet 5.5、Haiku 5.5 的逐檔分數，四模型比較全靠這兩份第三方資料。CursorBench 是 Cursor 的 harness（Cursor 也是 Anthropic 合作夥伴）；AA 的 Terminal-Bench 分數比 Anthropic 自報低 3 到 7 分。

**CursorBench 4.0**（真實 Cursor session 的模糊多檔任務；分數 / 每題成本＝API 單價 × 用量）

| effort | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 | Fable 5.1 |
|---|---|---|---|---|
| low | 30.9% / $0.08 | 35.8% / $0.37 | 43.7% / $1.17 | 45.1% / $5.44 |
| medium | 36.9% / $0.17 | 39.2% / $0.52 | 52.5% / $2.91 | 46.8% / $7.05 |
| high | 42.3% / $0.32 | 47.8% / $1.20 | 56.0% / $3.97 | 49.2% / $9.08 |
| xhigh | 44.3% / $0.56 | 53.1% / $2.81 | 56.0% / $6.98 | 51.6% / $13.01 |
| max | 48.4% / $1.12 | 55.5% / $7.05 | 57.8% / $13.43 | 51.8% / $17.28 |

**Artificial Analysis Intelligence Index**（10 項綜合評測；分數 / 每題成本 / 首字時間，含思考）

| effort | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 | Fable 5.1 |
|---|---|---|---|---|
| low | 29 / $0.02 | 36 / $0.35 / 0.6s | 42 / $0.55 / 12s | 未列 |
| medium | 34 / $0.05 / 13s | 41 / $0.48 / 0.9s | 51 / $1.34 / 28s | 49 / $2.98 / 12s |
| high | 38 / $0.08 / 25s | 47 / $0.88 / 14s | 54 / $1.82 / 57s | 51 / $3.91 / 18s |
| xhigh | 41 / $0.12 / 79s | 52 / $2.01 / 36s | 56 / $3.46 / 159s | 53 / $5.98 / 114s |
| max | 43 / $0.21 / 310s | 56 / $5.46 / 450s | 58 / $5.98 | 53 / $7.63 / 244s |

Haiku 的成本是暫定值，AA 還沒算進 100K 以上的價格級距。

**每升一檔多拿到什麼**（括號是每題成本增幅；SKILL.md 決策表的依據）

| 模型 | 升檔 | CursorBench | AA | 其他 | 判斷 |
|---|---|---|---|---|---|
| Opus 5.5 | medium → high | +3.5（+36%） | +3（+36%） | SWE-bench Pro +2.5；livenerf +4.2；首字 28s → 57s | 值得，四個來源一致 |
| Opus 5.5 | high → xhigh | +0（+76%） | +2（+90%） | SWE-bench Pro +1.4（+150%）；AA-Briefcase +75 Elo；首字 57s → 159s | 沒人等著的工作值得 |
| Opus 5.5 | xhigh → max | +1.8（+92%） | +2（+73%） | 貼上文字的植入指令照做率 2% → 7.4%；官方說容易想太多 | 只當 coding 卡關的升階 |
| Sonnet 5.5 | medium → high | +8.6（+131%） | +6（+83%） | | 值得 |
| Sonnet 5.5 | high → xhigh | +5.3（+134%） | +5（+128%） | FrontierCode 在這檔最高 | 值得 |
| Sonnet 5.5 | xhigh → max | +2.4（+151%） | +4（+172%） | FrontierCode -5.9；首字 450s | 不值得 |
| Haiku 5.5 | medium → high | +5.4（+88%） | +4（+60%） | | 值得 |
| Haiku 5.5 | high → xhigh | +2.0 | +3 | 多輪對話會空回覆 | 不值得 |
| Fable 5.1 | high → xhigh | +2.4（+43%） | +2（+53%） | 長交付物 token 約翻倍 | 非長交付物值得 |
| Fable 5.1 | xhigh → max | +0.2 | +0 | | 不值得 |

**各檔行為特性**（官方 prompting 指南、effort 文件與 System Card）
- Opus 5.5：low 拒絕隱藏的惡意子任務時常只在思考裡拒絕、不告訴你（p142）；medium 是 FrontierCode 最高分；high 多買驗證與邊界；xhigh 每回合想更多、回合更長，coding 跟 high 同分但知識型交付物還在漲（AA-Briefcase high 1705、xhigh 1780、max 1822）。
- Sonnet 5.5：low 簡單請求多半不思考、可能沒驗證就回報完成；medium 起幾乎每句都先想、長任務容易停下來問；xhigh 開始做自我審查回合，有時會開 subagent；max 叫它「做完就停、回報」可省約 1/3。每一檔都會多加沒要求的測試、文件、檔案，檔位越高越多。
- Haiku 5.5：low 長 prompt 會跳過搜尋、提早停、思考內容漏到輸出；medium 提早停止減半但仍會跳過驗證；high 是官方建議的嚴格照指令檔；xhigh 多輪對話會空回覆。
- Fable 5.1：low 搜尋變少、多靠記憶；high 會多改範圍外的小東西、整檔重寫、只描述下一步而不去做，派工單加「只碰要求的範圍」「把整件事做完」兩句可壓下來；xhigh 長交付物先在思考裡打草稿。

**10-03 本機實測**（`Projects\model-blackbox-eval\REPORT.md`）：題庫碰天花板（每格 96 份，最低 90），所以 medium 跟 high 沒差；opus@low 最差；max 三模型都沒增益；Sonnet 五檔都守 300 字上限，Opus 與 Fable 要 xhigh 以上。沒有測 Haiku 5.5。

## Claude Code 團隊實測

- **Claude Code 團隊實測**（Thariq，claude.dev「Spending your effort」2026-09-25；Terminal-Bench 3.0 內部跑法、每題 5 次、Fable 5.1 關安全防護，數字不能跟排行榜比）：
  - effort 主要改變驗證與邊界測試的量、以及自己下判斷的程度；檔位越高，替你做的假設越多。
  - 高 effort 修的是漏邊界不是方向錯：Fable 5.1 low→max 通過 140→214（共 370 次）、漏邊界類 59→24，但「選錯解讀」25→47 增加。
  - 最吃 effort 的領域（Fable 5.1 低檔→高檔通過率）：Security 64→87%、Hardware 34→75%；規則手冊型工作幾乎不動：Operations 12→22%、Media 18→30%。token 中位數 73k→222k。
  - Opus 5.5 例：儲存引擎 crash 修復 0/5→4/5（xhigh）、線性規劃 solver 0/5→5/5（high）、GSEA 分析 0/5→4/5（high），差別都在有沒有先重現、有沒有拿獨立解法對照測。
- 經驗法則與推薦迴圈在 SKILL.md「Effort 速查」。
