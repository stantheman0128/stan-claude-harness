# Effort 曲線與實測

SKILL.md「Effort 速查」與「升階路徑」的佐證。

## 官方曲線

- 舊實測曲線（Opus 5，僅供比例參考）：FrontierBench low 25% → high 39% → xhigh 44.4% → max 43%（不再漲）。
- **Opus 5.5 官方曲線（Opus 5.5 System Card §8）**：CursorBench medium 52.5% / high 56.0% / max 57.8%（p179）；GDPval-AA xhigh 1820 ≈ max 1846 但 output token 少 51%（p209）；AA-Briefcase xhigh 少 41% token（p210）；Terminal-Bench 4.0 xhigh 66.4 vs max 64.8「在雜訊內」（p178）；FrontierCode 1.1 在 medium 最高（54.6），medium 以上反而下降，因為高 effort 會改超出範圍的東西被扣分（p176）。FrontierCode 2.0 放寬了範圍評分（Fable 5.2 card SC pdf 209），Opus 5.5 在 2.0 版改成一路漲到 max，見下方 FrontierCode 2.0 表。
- **Fable 5.2 官方建議**（https://platform.claude.com/docs/en/build-with-claude/effort，2026-11-14 讀）：從 high 起，大部分能力增益在 high 就有了，再往上增益不均、看任務；xhigh 只給量過有增益的最難長程 coding 與 agentic 工作；max 留給量天花板或時間 token 都不在乎的少數任務；別沿用 Fable 5.1 的設定，重掃 effort。prompting 指南說 medium 升 high 是能力增益最大的一步，也最花 token。effort 幾乎不改回覆長度，長度與語氣靠 prompt 調。
- Opus 5.5 SWE-bench Pro（Anthropic effort 文件，以 high 為基準）：medium -2.5 分、成本約 70%；low -8 分、約 1/3；xhigh +1.4 分、約 2.5 倍。
- 「先低檔跑、失敗的再用高檔重跑」比全部高檔便宜：Opus 先 low、失敗題重跑 high 約 97% / $0.17，全部 high 是 95.3% / $0.29。每解出一題的成本：Opus 5.5 medium 92.8% / $0.22，Fable 5.1 預設 92.3% / $1.19。官方成本頁 2026-11 版：輸出可檢查時全部 low、失敗重跑 high，同通過率約省 40%。
- Haiku 5.5 GDPval-AA：max 1620、medium 1277（medium 只用 max 約 1/10 的 output token）。
- Sonnet 5.5 System Card 的 effort 細節在 `model-picks.md`；Fable 5.2 的分檔數字在 `fable52-system-card.md`。

## 各模型五檔

Anthropic 沒用文字公布 Sonnet 5.5、Haiku 5.5 的逐檔分數，跨模型比較靠第三方。CursorBench 是 Cursor 的 harness（Cursor 也是 Anthropic 合作夥伴）；AA 的 Terminal-Bench 分數比 Anthropic 自報低。

**CursorBench 4.0**（真實 Cursor session 的模糊多檔任務；分數 / 每題成本＝API 單價 × 用量。Haiku 到 Fable 5.1 是 2026-10-13 收集；Fable 5.2 是 2026-11-14 讀 Cursor 排行榜，分數與 Fable 5.2 card SC pdf 213 一致，Cursor 說有一部分來自 harness 改進，跟舊欄不完全可比）

| effort | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 | Fable 5.2 | Fable 5.1（legacy） |
|---|---|---|---|---|---|
| low | 30.9% / $0.08 | 35.8% / $0.37 | 43.7% / $1.17 | 53.2% / $3.94 | 45.1% / $5.44 |
| medium | 36.9% / $0.17 | 39.2% / $0.52 | 52.5% / $2.91 | 54.8% / $4.66 | 46.8% / $7.05 |
| high | 42.3% / $0.32 | 47.8% / $1.20 | 56.0% / $3.97 | 56.9% / $9.70 | 49.2% / $9.08 |
| xhigh | 44.3% / $0.56 | 53.1% / $2.81 | 56.0% / $6.98 | 56.3% / $15.48 | 51.6% / $13.01 |
| max | 48.4% / $1.12 | 55.5% / $7.05 | 57.8% / $13.43 | 60.0% / $32.79 | 51.8% / $17.28 |

**Artificial Analysis Intelligence Index v5.0.1**（9 項綜合評測；分數 / 每題美元 / 每題秒數，秒數是每題平均完成時間，含思考。Haiku、Sonnet、Opus、Fable 5.2 是 2026-11-23 讀 artificialanalysis.ai 各家族模型頁內嵌的 initialModels 數據；Fable 5.1 是 2026-11-14 同版本的讀數。跟 10-18 的 v4.3.2 表分數尺度不同，不能混著比）

| effort | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 | Fable 5.2 | Fable 5.1（11-14） |
|---|---|---|---|---|---|
| low | 18.6 / 0.04 / 129 | 25.6 / 0.51 / 155 | 34.8 / 0.98 / 183 | 53.9 / 3.10 / 333 | 38.7 / 4.47 / 449 |
| medium | 24.6 / 0.09 / 243 | 30.8 / 0.78 / 220 | 48.2 / 2.45 / 407 | 56.4 / 3.80 / 395 | 43.2 / 5.56 / 586 |
| high | 29.9 / 0.16 / 388 | 41.5 / 1.64 / 416 | 51.8 / 3.46 / 558 | 61.8 / 9.08 / 887 | 47.2 / 7.54 / 796 |
| xhigh | 34.6 / 0.25 / 571 | 49.9 / 4.09 / 839 | 57.4 / 6.05 / 936 | 62.2 / 14.83 / 1460 | 50.0 / 10.85 / 1146 |
| max | 36.5 / 0.41 / 879 | 54.5 / 10.02 / 1884 | 59.1 / 10.04 / 1513 | 64.6 / 26.54 / 2485 | 49.2 / 12.99 / 1339 |

網址：https://artificialanalysis.ai/models/claude-haiku-5-5 、/claude-sonnet-5-5 、/claude-opus-5-5 、/claude-fable-5-2（2026-11-23 讀）。各檔位的獨立網址（例如 `-high`）現在 308 轉回家族頁，數值取自家族頁 initialModels 陣列裡帶檔位後綴的 slug。Sonnet low 到 high、Haiku low 到 xhigh 只出現在自家家族頁，沒有第二頁可交叉核對。Opus 與 Fable 5.2 的分數與成本跟 11-14 讀數逐位相同，只有秒數小幅變動。

**AA 逐項拆分**（同上來源，2026-11-23 從家族頁抽出；Briefcase 是 Elo，GDPval 已不在 v5 總分裡但頁面仍列；HLE 是 v5 用的 HLE Diamond；幻覺率是 AA-Omniscience hallucination rate，越低越好，量的是答不出來時硬掰的比例，跟 System Card 的「輸入幻覺」不是同一件事；FC-AA 是 AA 自己跑的 FrontierCode 2.0）

| 變體 | 總分 | Terminal-Bench 4.0 | Briefcase | GDPval | AutomationBench | HLE Diamond | 幻覺率 | FC-AA 2.0 |
|---|---|---|---|---|---|---|---|---|
| Opus low | 34.8 | 31.3 | 1278 | 1239 | 52.9 | 41.7 | 0.66 | 15.8 |
| Opus medium | 48.2 | 52.5 | 1615 | 1590 | 61.2 | 51.4 | 0.67 | 33.1 |
| Opus high | 51.8 | 56.6 | 1682 | 1709 | 63.2 | 55.6 | 0.64 | 35.9 |
| Opus xhigh | 57.4 | 59.6 | 1758 | 1836 | 65.0 | 64.0 | 0.65 | 43.8 |
| Opus max | 59.1 | 59.6 | 1797 | 1866 | 69.5 | 67.9 | 0.50 | 46.4 |
| Sonnet low | 25.6 | 20.7 | 1268 | 1182 | 49.4 | 20.6 | 0.48 | 7.1 |
| Sonnet medium | 30.8 | 29.8 | 1436 | 1326 | 54.9 | 23.8 | 0.50 | 11.0 |
| Sonnet high | 41.5 | 43.9 | 1633 | 1551 | 59.4 | 33.8 | 0.64 | 25.7 |
| Sonnet xhigh | 49.9 | 57.1 | 1736 | 1743 | 65.5 | 44.1 | 0.62 | 35.7 |
| Sonnet max | 54.5 | 63.6 | 1813 | 1838 | 71.8 | 53.3 | 0.43 | 41.7 |
| Haiku low | 18.6 | 12.6 | 1112 | 1130 | 22.9 | 14.1 | 0.41 | 8.0 |
| Haiku medium | 24.6 | 15.2 | 1364 | 1282 | 28.6 | 16.8 | 0.40 | 16.1 |
| Haiku high | 29.9 | 21.7 | 1440 | 1424 | 33.7 | 23.7 | 0.39 | 23.2 |
| Haiku xhigh | 34.6 | 29.3 | 1522 | 1523 | 36.0 | 28.8 | 0.39 | 29.9 |
| Haiku max | 36.5 | 32.8 | 1571 | 1629 | 35.4 | 29.6 | 0.34 | 34.9 |
| Fable 5.2 low | 53.9 | 54.6 | 1564 | 1546 | 68.0 | 60.8 | 0.56 | 38.4 |
| Fable 5.2 medium | 56.4 | 55.1 | 1623 | 1591 | 68.8 | 66.3 | 0.58 | 41.3 |
| Fable 5.2 high | 61.8 | 59.6 | 1677 | 1718 | 71.4 | 73.8 | 0.58 | 49.1 |
| Fable 5.2 xhigh | 62.2 | 61.6 | 1737 | 1751 | 74.2 | 75.8 | 0.60 | 47.6 |
| Fable 5.2 max | 64.6 | 59.6 | 1783 | 1831 | 76.4 | 80.2 | 0.59 | 48.8 |

Fable 5.1 的 v5.0.1 拆分（2026-11-14 讀，`fable52-evidence.json`）：Terminal-Bench 40.4 / 44.9 / 52.0 / 55.1 / 52.0，Briefcase 1478 / 1525 / 1577 / 1649 / 1670，low 到 max。

從這兩張 AA 表讀出的五點（2026-11-23 寫進 SKILL.md）：
1. Sonnet xhigh 每題仍比 Opus high 貴（4.09 對 3.46 美元）、分數略低（49.9 對 51.8）、慢 1.5 倍；fan-out 選 Sonnet 的理由仍只有分散週額度。
2. Opus xhigh → max 的 Terminal-Bench 仍是 0 增益（59.6 對 59.6），漲分在 Briefcase +39、GDPval +30、HLE Diamond +3.9、AutomationBench +4.6，幻覺率 0.65 → 0.50；每題成本 1.66 倍。
3. Sonnet max 的 Terminal-Bench 63.6 仍是 Anthropic 全系列最高（Fable 5.2 最高是 xhigh 61.6）；AutomationBench 71.8 已被 Fable 5.2 high 以上超過。代價從 10-18 的每題 5.46 美元、905 秒變成 10.02 美元、1884 秒。
4. Fable 5.2 high（61.8、每題 9.08 美元）已高過 Opus max（59.1、10.04 美元）；但同檔比，Briefcase 與 GDPval 是 Opus 高。
5. Fable 5.2 medium → high 是它最大的一跳（+5.4，成本 2.4 倍）；high → xhigh 只 +0.4；xhigh → max 的 Terminal-Bench 從 61.6 退到 59.6。

**FrontierCode 2.0（Cognition 排行榜）**（https://cognition.com/frontiercode，2026-11-23 讀，資料檔 Last-Modified 2026-11-21；所有結果 2026-11-11 重算過，五個模型都跑 claude-code harness；分數是 rubric 加權總分，每 rollout 美元依官方價。跟 Fable 5.2 card SC pdf 209 的數字不同，card 是重算前的版本）

| effort | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 | Fable 5.2 | Fable 5.1 |
|---|---|---|---|---|---|
| low | 10.6% / $0.07 | 9.7% / $0.37 | 14.8% / $0.75 | 35.3% / $2.62 | 21.2% / $3.01 |
| medium | 14.1% / $0.10 | 15.0% / $0.48 | 31.4% / $1.70 | 38.8% / $3.10 | 22.3% / $3.89 |
| high | 19.3% / $0.14 | 22.9% / $1.07 | 36.3% / $2.42 | 46.2% / $8.40 | 26.6% / $5.39 |
| xhigh | 22.9% / $0.23 | 36.5% / $3.31 | 44.7% / $5.18 | **50.2%** / $17.73 | **34.0%** / $8.68 |
| max | **28.9%** / $0.37 | **42.2%** / $19.94 | **47.3%** / $12.82 | 48.2% / $55.87 | 33.0% / $11.46 |

粗體是各模型最高分。Opus 5.5、Sonnet 5.5、Haiku 5.5 一路漲到 max；Fable 5.1 與 Fable 5.2 在 xhigh 最高，max 反而退。Fable 5.2 xhigh 是全榜 35 個模型第一。Sonnet xhigh → max 多 5.7 分、成本 6 倍；Opus xhigh → max 多 2.6 分、成本 2.5 倍；Fable 5.2 xhigh → max 少 2.0 分、成本 3.2 倍。Fable 5.2 high（46.2、8.40 美元）對 Opus 最佳 max（47.3、12.82 美元）：少 1.1 分、成本約 2/3。Sonnet xhigh（36.5）跟 Opus high（36.3）同分。表只公布 output token，沒有 input 與總 token。

**每升一檔多拿到什麼**（括號是每題成本增幅；AA 用 v5.0.1；SKILL.md 決策表的依據）

| 模型 | 升檔 | CursorBench | AA | FrontierCode 2.0 | 其他 | 判斷 |
|---|---|---|---|---|---|---|
| Opus 5.5 | medium → high | +3.5（+36%） | +3.6（+41%） | +4.9 | SWE-bench Pro +2.5；livenerf +4.2 | 值得，各來源一致 |
| Opus 5.5 | high → xhigh | +0（+76%） | +5.6（+75%） | +8.4 | SWE-bench Pro +1.4（+150%）；Briefcase +76 | 沒人等著的工作值得 |
| Opus 5.5 | xhigh → max | +1.8（+92%） | +1.7（+66%） | +2.6（+147%） | AA：Terminal-Bench +0、Briefcase +39、GDPval +30、HLE Diamond +3.9、幻覺率 0.65 → 0.50；貼上文字的植入指令照做率 2% → 7.4% | 知識型長交付物要準確時值得；coding 證據偏弱；都由 Stan 決定 |
| Sonnet 5.5 | medium → high | +8.6（+131%） | +10.7（+110%） | +7.9 | | 值得 |
| Sonnet 5.5 | high → xhigh | +5.3（+134%） | +8.4（+150%） | +13.6 | | 值得 |
| Sonnet 5.5 | xhigh → max | +2.4（+151%） | +4.6（+145%） | +5.7（+502%） | AA：Terminal-Bench +6.6、AutomationBench +6.2、幻覺率 0.62 → 0.43；每題 1884 秒 | 不當起點；Opus xhigh 也卡關的終端機任務可當候選 |
| Haiku 5.5 | medium → high | +5.4（+88%） | +5.3（+73%） | +5.2 | | 值得 |
| Haiku 5.5 | high → xhigh | +2.0 | +4.8（+57%） | +3.6 | 多輪對話會空回覆；VulcanBench 反而更好（見觀察項） | 照規則不開，列觀察項 |
| Fable 5.2 | medium → high | +2.1（+108%） | +5.4（+139%） | +7.4 | 官方：增益最大的一步 | 值得，升級後的起點 |
| Fable 5.2 | high → xhigh | -0.6（+60%） | +0.4（+63%） | +4.0（+111%） | FrontierCode 的最高點 | 長程 agentic coding 值得 |
| Fable 5.2 | xhigh → max | +3.7（+112%） | +2.3（+79%） | -2.0（+215%） | ARC-AGI-3 high 79.26 → max 65.66（SC pdf 243）；Terminal-Bench（AA）61.6 → 59.6 | 不當預設 |

Fable 5.1 的升檔數字留在 10-18 版（high → xhigh CursorBench +2.4；xhigh → max +0.2），只當 legacy 參考。

**各檔行為特性**（官方 prompting 指南、effort 文件與 System Card）
- Opus 5.5：low 拒絕隱藏的惡意子任務時常只在思考裡拒絕、不告訴你（p142）；high 多買驗證與邊界；xhigh 每回合想更多、回合更長，知識型交付物還在漲（Briefcase high 1682、xhigh 1758、max 1797）。
- Sonnet 5.5：low 簡單請求多半不思考、可能沒驗證就回報完成；medium 起幾乎每句都先想、長任務容易停下來問；xhigh 開始做自我審查回合，有時會開 subagent；max 叫它「做完就停、回報」可省約 1/3（官方段落逐字在 SKILL.md 硬規則 15）。每一檔都會多加沒要求的測試、文件、檔案，檔位越高越多。
- Haiku 5.5：low 長 prompt 會跳過搜尋、提早停、思考內容漏到輸出；medium 提早停止減半但仍會跳過驗證；high 是官方建議的嚴格照指令檔；xhigh 多輪對話會空回覆。
- Fable 5.2：low 跑測試比 Fable 5.1 少、會講程式碼撐不住的肯定句（SC pdf 34）；low 與 medium 在長任務較常提早結束回合（列出剩下什麼、問要不要繼續、碰到普通障礙就停，prompting 指南）；medium 開放式研究題 63% 沒跑實驗就收手（SC pdf 34）；high 以上幾乎每則回覆前都會思考，叫它「直接答」不會少想，要少想就降檔（prompting 指南）；告訴它「你擁有這個 codebase」會大量整併重複程式碼，output token 多 70% 到 80%，還會改沒要求的東西（prompting 指南）。
- Fable 5.1（legacy）：low 搜尋變少、多靠記憶；high 會多改範圍外的小東西、整檔重寫、只描述下一步而不去做；xhigh 長交付物先在思考裡打草稿。

**10-03 本機實測**（`Projects\model-blackbox-eval\REPORT.md`）：題庫碰天花板（每格 96 份，最低 90），所以 medium 跟 high 沒差；opus@low 最差；max 三模型都沒增益；Sonnet 五檔都守 300 字上限，Opus 與 Fable 要 xhigh 以上。沒有測 Haiku 5.5 與 Fable 5.2。

## Fallback 會吃掉多少（分類器擋下後改由別的模型回答）

AA 把 Sonnet 5.5、Opus 5.5、Fable 5.2 的每個變體都標「Default Fallback」，Haiku 5.5 沒標；AA 頁面沒定義這個標籤（2026-11-23 查）。Stan 設了 `switchModelsOnFlag: false`，在 Claude Code 裡被標記時 session 暫停，不會默默改送 fallback 模型；第三方分數則是開著 fallback 跑的。

- **VulcanBench Frontier v4（舊名 SWE v4），Opus 5.5**（https://vulcanbench.com/benchmarks/swe-v4-opus55-v315.html#fallback ，2026-11-23 讀；報告 2026-09-26，Claude Code 2.1.280、Max 訂閱，每格 23 次）：回覆由 Opus 4.8 產生的比例，low 0.0%、medium 6.4%、high 20.9%、xhigh 32.4%、max 47.8%（有 Opus 4.8 回合的 run：0、3、7、8、12 次）。頁面說 max 幾乎是兩個模型各半，高檔分數有一部分其實在量 Opus 4.8。high 有一次被分類器停下、留下空 patch 算 0 分。
- **VulcanBench，Fable 5.2**（https://vulcanbench.com/benchmarks/swe-v4-fable52-v330.html ，2026-11-23 讀；報告 2026-11-13，Claude Code 2.1.321）：fallback 開著但從沒接手，115 次全由 `claude-fable-5-2` 回答。這組是良性 coding 題。
- **Fable 5.2 System Card 的 fallback 比率**（偏攻擊與資安情境，比 Opus 5.5、Fable 5.1 高很多）：Gray Swan IPI 被改送 Opus 4.8 的比例 Fable 5.2 53%、Fable 5.1 23%、Opus 5.5 18%（SC pdf 85）；Shade coding 攻擊 Fable 5.2 99.5%、Opus 5.5 64%、Fable 5.1 60%（SC pdf 87）；Terminal-Bench 4.0 這種良性科學工程題，Fable 5.2 與 Opus 5.5 都是 2.5% 的請求被標記、影響 10% 的 trial（SC pdf 211）。
- Claude Code 自動 fallback 時，被標記那則請求的 effort 會帶到 fallback 模型（https://code.claude.com/docs/en/model-config ，2026-11-14 讀）。

## 觀察項：Haiku 5.5 xhigh

規則仍是 Haiku 不開 xhigh（多輪對話會空回覆，官方說法）。2026-11-23 收集到的反向數據先記在這裡，不改規則：
- VulcanBench（https://vulcanbench.com/benchmarks/swe-v4-haiku55-v324.html ，報告 2026-10-12）：通過題數 low 13、medium 13、high 17、xhigh 22、max 22（共 23 題）；xhigh 每題 0.84 美元、19.0 分鐘，比 high 的 1.25 美元、26.8 分鐘更便宜也更快，是五檔裡最省的一檔；fallback 開著但從沒用到。
- AA v5.0.1：high 29.9 → xhigh 34.6（+4.8），每題 0.16 → 0.25 美元。
- FrontierCode 2.0：high 19.3 → xhigh 22.9，每 rollout 0.14 → 0.23 美元。
- 要改規則前要先在自己的多輪 fan-out 上測空回覆率；這些都是單輪或 agent 型評測。

## Claude Code 團隊實測

- **Claude Code 團隊實測**（Thariq，claude.dev「Spending your effort」2026-09-25；Terminal-Bench 3.0 內部跑法、每題 5 次、Fable 5.1 關安全防護，數字不能跟排行榜比）：
  - effort 主要改變驗證與邊界測試的量、以及自己下判斷的程度；檔位越高，替你做的假設越多。
  - 高 effort 修的是漏邊界不是方向錯：Fable 5.1 low→max 通過 140→214（共 370 次）、漏邊界類 59→24，但「選錯解讀」25→47 增加。
  - 最吃 effort 的領域（Fable 5.1 低檔→高檔通過率）：Security 64→87%、Hardware 34→75%；規則手冊型工作幾乎不動：Operations 12→22%、Media 18→30%。token 中位數 73k→222k。
  - Opus 5.5 例：儲存引擎 crash 修復 0/5→4/5（xhigh）、線性規劃 solver 0/5→5/5（high）、GSEA 分析 0/5→4/5（high），差別都在有沒有先重現、有沒有拿獨立解法對照測。
- 經驗法則與推薦迴圈在 SKILL.md「Effort 速查」。
