# 模型選擇細節：Fable 5.1、Sonnet 5.5、Haiku 5.5

SKILL.md 決策表與「Fable 5.1、Sonnet 5.5、Haiku 5.5 的界線」的佐證，數字附出處頁碼。

## Fable 5.1 還值得選的情境（誠實版）

發佈文的 benchmark 全部 Opus 5.5 領先或持平，且官方自己說「差距比分數看起來更小」。System Card 翻遍 §8 只找到這幾個 Fable/Mythos 5.1 還贏的點（全是小差距）：OfficeQA 80.2 vs 78.9、OfficeQA Pro 69.0 vs 67.7（p208）；Toolathlon Pass^3（三次全對）73.1 vs 72.2（p210，這項 Pass@1 最高的其實是 Opus 5 的 80.6，Opus 5.5 與 Fable 都開著分類器跑）；Mythos 5.1 在 LatchBio SpatialBench 77.6 vs 72.0、BioMysteryBench Human Solvable 90.3 vs 89.3（p217）。剩下的理由都是情境性的：

1. **Opus 5.5 @ xhigh/max 評測仍不及格**的深推理或長程任務：官方唯一明示的升級路徑。Card 裡沒有任何 coding/agentic benchmark 是 Fable 贏的，所以這條要「先量再換」。
2. **對話中途升級不丟推理**：Fable 5.1 讀得懂 Opus 5.5 的 thinking block，反向不行。Opus 5.5 → Fable 5.1 保留整段推理；Opus 5.5 → Sonnet/Opus 5、或 Fable → Opus 5.5 都會丟掉切換前的推理。
3. **已校準的 Fable prompt/評測不想重跑**：Opus 5.5 同檔位思考量比 Opus 5 多，換模型要重掃 effort。
4. **額度桶**：Max 方案上 Fable 有獨立 weekly 額度（quota-pacer 已納管）；Opus 5.5 是否與 Opus 5 同桶未查證。Opus 桶快爆時 Fable 是備援算力。
5. 安全/cyber：分類器同級，換 Fable 不會比較少被擋，所以不用 Fable 起手。唯一反例是 Endor Labs 的弱點修補測試（179 題，Claude Code harness）：功能通過率 Fable 87.2%、Opus 68.7%，Opus 有 51 題是背出訓練資料。只有這一份、effort 沒標，Vals 的資安分數排序也怪（Haiku 高於 Fable），所以只當「Opus 5.5 @ xhigh 修不好的弱點，可建議 Fable 5.1 @ xhigh」（2026-10-13 定）。
6. 誠實向贏 Opus 5.5 的是 **Mythos 5.1** 不是 Fable：「沙盒裡有答案就偷用不講」與閃躲敏感問題兩項 Mythos 5.1 較好（p110、p131）；card 文字沒點名 Fable 5.1 的對應結果。
7. 網傳「Fable 架構/洞見比 Opus 5.5 強」：**兩份 card 都沒數據支持，反而寫了同一種弱點**（2026-09-25 查）。Fable/Mythos 5.1 card p32：開放式構想與設計能力弱、策略判斷差，會順著使用者給的框架延伸而不挑戰它。Opus 5.5 card p33/p36：不提超出文獻的新點子；處理 review 意見只改局部、沒回頭檢查整體設計；拿自己寫的需求驗收計畫。METR 評 Opus 5.5 的 judgement/taste 沒比 Fable 5.1 大幅進步（p43），CoBench 2.1 三顆在誤差內（p37）。支持這句話的只有使用者體感（Every Vibe Check：有人大題仍偏好 Fable）。對策：架構題不必因此換 Fable；prompt 明講「先探索再動手、挑戰我的前提、改完回頭檢查整體設計」；真要比就同一份 brief 兩顆各跑一次。

## Sonnet 5.5 什麼時候選（2026-09-28 發佈）

官方定位：「strongest at well-scoped everyday tasks, fixing bugs, and creating polished documents, slides, and spreadsheets」；開放式、需要長時間判斷的工作「Opus 5.5 remains clearly stronger」。預設模型仍是 Opus 5.5。

| 發佈文 benchmark | Sonnet 5.5 | Opus 5.5 | Sonnet 5 |
|---|---|---|---|
| Terminal-Bench 4.0 | **70.6** | 66.4 | 10.3 |
| FrontierCode 1.1 | 52.1（xhigh）/ 46.2（max） | 54.4 | 42.4 |
| CursorBench 4.0 | 55.5 | 57.8 | 34.1 |
| GDPval-AA | 1844 | 1846 | 1449 |
| HLE with tools | 64.5 | 67.7 | 54.9 |
| OSWorld 2.1 | 80.1 | 81.8 | 57.0 |

1. **選它**：任務有清楚 spec 和驗收方法（測試、型別檢查、build）、修既有 bug、產文件/簡報/試算表、量大的 subagent 派工。
2. **high 才是 Sonnet 最划算的一檔**（2026-10-13 依第三方數據改寫）：官方說「complements Opus 5.5 best when running at lower effort settings… At higher settings, it can perform comparably at a similar cost」，但 CursorBench 上 Sonnet high 只要 Opus medium 成本的 41%（AA 上 66%），要到 xhigh 才跟 Opus medium 同分同價。所以 Sonnet 開 high；xhigh 用在 fan-out，目的是吃 Sonnet 自己的週上限、不搶 Opus 額度。逐檔數字在 `effort-evidence.md`。
3. **不選它**：開放式、長程、要持續判斷的活（官方原話：最難的長程工作 Opus 比較好）；開到 xhigh 還過不了的任務（換 Opus 5.5 @ high，不開 Sonnet max）。
4. **max 通常比 xhigh 差**：FrontierCode max 46.2 < xhigh 52.1，發佈文腳註說 max 較常自己跑 code-review skill、拆大量 subagent，結果逾時或改超出範圍。例外是 CursorBench（max 55.5 > xhigh 53.1），但成本翻倍以上（見下方 System Card）。
5. **要不要從 Opus 降 Sonnet，自己量**：`/claude-api build-eval` 建評測、`/claude-api hillclimb` 調 prompt（CC v2.1.259 起）。官方案例（客服問答）：prompt 瘦身後 Sonnet 5 @ low 88.9% 每題約 1¢，贏 Opus 5.5 @ low 87.8% 每題 1.9¢。
6. 發佈文沒放 Fable 5.1；System Card 的表裡 Sonnet 5.5 幾乎全贏 Fable 5.1（Terminal-Bench 70.6 vs 55.8、GDPval 1844 vs 1735），只輸多語 GMMLU（p140）。

**System Card 重點**（Claude Sonnet 5.5 System Card，2026-09-28，148 頁，全文讀過並抽查引句；「圖讀」＝從圖目測、卡片內文沒寫數字）
- **差距在寫 code 與長 context**：SWE-Bench Pro 81.3 vs Opus 5.5 89.9（p109）；ProgramBench 1M 視窗 79.7 vs 91.2（p118）。贏或平的是終端機、自動化、知識工作：AutomationBench 44.7 vs 42.5、Toolathlon 77.8 平手（p109、p134）。
- **effort**：多數評測 xhigh 最划算，max 常更差且 token 暴增；GDPval xhigh 比 max 少 67% output token（p133）。CursorBench medium 39.2 / high 47.8 / xhigh 53.1 / max 55.5（p115）。每題成本以 Cursor 2026-10-07 依調整後價格重算的版本為準：medium $0.52、high $1.20、xhigh $2.81、max $7.05，Opus 5.5 medium 52.5% / $2.91（System Card 圖上讀到的 $0.7 / $3.9 / $9.7 是調價前的舊值）。Sonnet xhigh（53.1% / $2.81）跟 Opus 5.5 medium 分數與成本都差不多；主 session 直接用 Opus，fan-out 用 Sonnet xhigh 分攤額度。
- **分類器**：bio 沿用 Opus 5 那套（比 Opus 5.5 窄，無 fallback，p10、p19）；cyber 政策同 Opus 5.5，官方明說連無害的資安任務也會多被擋（p28）；編譯後 binary 找漏洞一律不幫（p29）。API 要開發者 opt-in 才自動 fallback（p29）。
- **Prompt injection**：Sonnet 5.5 自己回答的 5,901 個 coding 攻擊請求只被攻破 4 個，破口一樣在 fallback 到 Sonnet 5 之後（p52）；瀏覽器情境是第一個 0 成功的模型（p54）；Gray Swan 比 Opus 5.5 與 Fable 5.1 弱（p50）。**卡片沒做「使用者貼上文字」這項測試**，當作跟 Opus 5.5 一樣要防（見 `opus55-system-card.md`「使用 Opus 5.5 的對策」第 1 條）。
- **行為**：誠實指標除了閃躲都比 Sonnet 5 好；被施壓時比 Opus 5.5 誠實，但幻覺較多（p56、p65）。魯莽程度只有 Opus 5.5 嚴格更好（p65）。有會把任務卡當成授權的案例（p60）。推理文字是測過最難讀的（p72），自建監控靠讀 thinking 會比較吃力。每段 transcript 輸出 token 偏多（p84）。
- **沒測的不等於沒問題**：早停、破壞性動作專項、訓練期 reward hacking 審查都沒重做（p58）。無人值守長任務照 Opus 5.5 的對策處理。

## Haiku 5.5 什麼時候選（2026-10-07 發佈）

官方定位：「designed for high-volume, cost-sensitive tasks」，例如摘要、compaction、資料庫查詢、分類；「It pairs well with Opus 5.5 and Sonnet 5.5 as a subagent on coding work」，但「Sonnet 5.5 and Opus 5.5 remain better choices for complex agentic coding tasks」。第一個能調 effort 的 Haiku。

| 規格 | Haiku 5.5 |
|---|---|
| 價格 in/out（$/MTok） | $0.10/$0.50（prompt ≤100K）；$0.50/$2.50（>100K） |
| cache read / write | $0.01 / $0.125（>100K：$0.05 / $0.625） |
| context | 1M（所有方案） |
| CC 預設 effort | medium；五檔都支援 |
| tokenizer | 跟 Sonnet 5.5、Opus 5.5 同一套，同文字比 Haiku 4.5 約多 30% token |
| API | adaptive thinking 預設開；不要送 `temperature`/`top_p`/`top_k`；Haiku 5.5 不能當 advisor（被諮詢的那一方），自己當主模型時可以諮詢 Opus advisor |

發佈文 benchmark（effort 沒標，多半是 max）：GDPval-AA 1620（Haiku 4.5 735）、Terminal-Bench 4.0 39.2（Sonnet 5.5 70.6）、FrontierCode 1.1 46.4（Sonnet 5.5 xhigh 52.1）。

1. **選它**：大量抽取、分類、摘要，輸出可以逐條檢查。effort 開 high（medium → high CursorBench +5.4）；prompt 維持 100K 以內，超過單價變 5 倍。
2. **不選它**：要判斷的實作、安全、複驗、scout。System Card 裡它在「輸入幻覺、重要遺漏、謊報完成」三項都輸 Opus 5.5 與 Sonnet 5.5，輸入幻覺跟 Haiku 4.5 一樣多。
3. **雷點**：17% 會偷用外洩的答案而不說；過度拒絕是所有模型最多；30% 的情境會碰沙箱外的東西，system prompt 加一段沙箱說明降到 1.8%；cyber 防護會擋滲透測試等攻擊方較常用的技術。
4. **強項**：最便宜、最快（約 238 token/s）；對抗式 coding prompt injection 成功率 0.08%，沒有 fallback 路徑可鑽。讀不受信任的內容、手上又有破壞性工具的 agent，它反而比 Opus 穩（見 `opus55-system-card.md` 的 5.5 世代安全發現）。
