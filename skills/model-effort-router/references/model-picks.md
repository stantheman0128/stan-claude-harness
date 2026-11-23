# 模型選擇細節：Fable 5.2、Mythos 5.2、Sonnet 5.5、Haiku 5.5

SKILL.md 決策表與「Fable 5.2、Mythos 5.2、Sonnet 5.5、Haiku 5.5 的界線」的佐證，數字附出處頁碼。Fable 5.2 card 寫成「SC pdf N」（PDF 頁），其他 card 沿用 pN。

## Fable 5.2 什麼時候選（2026-11-09 發佈）

官方定位：所有客戶都能用的最強模型；多數工作先用 Opus 5.5，Opus 5.5 在較高 effort 的評測仍不夠，或是要求很高的推理與長程 agentic 工作，才換 Fable 5.2（https://platform.claude.com/docs/en/about-claude/models/choosing-a-model ，2026-11-14 讀）。Stan 的規則更嚴：Opus 5.5 @ high 與 xhigh 各試 2 次仍失敗，回報 Stan 由他決定（Fable 有自己的週額度）。

**它贏 Opus 5.5 的地方**（Fable 5.2 card 與第三方）
1. **coding**：SWE-bench Pro 93.0 對 89.9（SC pdf 207 到 208）。FrontierCode 2.0：card 版 high 45.3 跟 Opus 最佳 45.5 差不多，每題 6.72 對 12.82 美元，約一半成本；xhigh 49.1 是最高（SC pdf 209）。Cognition 2026-11-11 重算後的排行榜是 high 46.2（8.40 美元）對 Opus 最佳 47.3（12.82 美元），xhigh 50.2 全榜第一（https://cognition.com/frontiercode ，2026-11-23 讀）。
2. **多小時自主工程**：FrontierSWE v2（34 題、每題約 20 小時的超長程工程）69.9 對 62.3，效能優化、科學計算、視覺推理拉開最多（SC pdf 212）。Remote Labor Index（用 240 個真實外包案測 agent）41.3 對 21.3，兩邊都用預設 high（SC pdf 242）。
3. **AA 總分**：Fable 5.2 high 61.8（每題 9.08 美元）已高過 Opus max 59.1（10.04 美元）（AA v5.0.1，2026-11-23 讀）。
4. **有可爬坡訊號的難題**：第三方評測機構 METR 認為它在可驗證任務上比 Fable 5.1 明顯進步（SC pdf 40）；ARC-AGI-3（沒給規則、要自己摸出目標的回合制遊戲）high 79.26%（SC pdf 243）。
5. **讀圖不給工具**：Chartography 沒工具 73.4 對 64.4，給容器與裁圖工具後只差 2.6 分（SC pdf 229）。
6. VulcanBench Frontier v4：五檔都 23/23 通過、max 綜合分 93.85 全榜第一，Opus 5.5 最佳 91.11（high）；評審組合不同，Fable 5.2 這欄由 Muse 與 GPT-6.1 Sol 評，頁面說 Sol 給 code 的分數約高 7 分，不能嚴格比（https://vulcanbench.com/benchmarks/swe-v4-fable52-v330.html ，2026-11-23 讀）。

**Opus 5.5 仍贏或打平的地方**
1. **專業知識交付物**：GDPval-AA 1866 對 1831、AA-Briefcase Elo（拿成品兩兩比較算出的相對分）1800 對 1785（SC pdf 207、239）。文件、簡報、試算表這類長交付物留在 Opus。
2. **終端機為主的 agent 任務**：Terminal-Bench 4.0 Fable 5.2 max 67.6 對 Opus 5.5 xhigh 66.4，在雜訊內（SC pdf 211）。AA 版 Terminal-Bench 也一樣，Fable 5.2 最高 61.6（xhigh），Sonnet 5.5 max 63.6 還更高。
3. **單一長 context**：ProgramBench Fable 5.2 85.6、Opus 91.2；Fable 5.2 有 68% 的題目在交件前用完 context。harness 每步告訴它剩多少 context 才升到 91.6，跟 Opus 91.1 打平（SC pdf 216）。Claude Code 會自動 compact，自寫迴圈要自己給。
4. **讀不受信任內容**：Fable 5.2 的 fallback 比率最高，攻擊成功率因此較高（Gray Swan 間接 prompt injection 測驗 53% 被改送 Opus 4.8，Opus 5.5 18%，SC pdf 85；Shade coding 89.82% 對 54.61%，SC pdf 87）。
5. **AutomationBench low 檔**：Fable 5.2 low 39.7 低於 Opus max 42.5（SC pdf 241）；Fable 5.2 不要開 low。

**effort**：high 是升級後的起點（官方預設、PhysicianBench xhigh 與 max 對 high 沒有可分辨的增益，SC pdf 247）；長程 agentic coding 用 xhigh（FrontierCode 2.0 最高點）；max 不當預設（FrontierCode 與 ARC-AGI-3 在 max 退步，CursorBench 與 AA 對 high 多約 3 分但 token 或成本約 3 倍）；medium 升 high 是最大的一跳；不開 low。細節在 `effort-evidence.md`。

**不要期待它修掉的問題**：METR 說它跟 Opus 5.5 有同樣的弱點，不會建高效回饋迴圈、該轉向時還在小修小補（SC pdf 41）；Opus 在原地打轉時，先自己逼它重新規劃，換 Fable 不會自動好。自我批評在它誤判缺陷嚴重度時無效（SC pdf 31）。用法上的防護見 `fable52-system-card.md`。

**多 agent**：小隊只換到速度不換到分數，token 更多（SC pdf 223、225），Fable 5.2 單 agent 跑。

**Fable 5.1（legacy）**：仍可用（`/model claude-fable-5-1`，退役不早於 2027-09-01），價格 10/50 美元。Fable 5.1 時期「Opus 5.5 幾乎全贏」的結論只適用 Fable 5.1；Endor Labs 弱點修補（Fable 5.1 87.2% 對 Opus 68.7%，179 題、effort 沒標）也是 Fable 5.1 的資料，Fable 5.2 沒有對應數字。

## Mythos 5.2 什麼時候選

- **是什麼**：`claude-mythos-5-2`，跟 Fable 5.2 同一個模型、同規格同價，只是放寬資安與生科 safeguards；reduced classifiers 仍在（SC pdf 2、47；https://platform.claude.com/docs/en/models/fable-5-2/overview ，2026-11-14 讀）。只開給通過資安驗證計畫（CVP）或生科驗證計畫的組織。
- **Stan 能用**：2026-11-23 實測 `claude -p --model claude-mythos-5-2` 有回答，usage 顯示 `claude-mythos-5-2`。走哪一個週額度桶查不到（Mythos 5.1 時期官方寫跟 Fable 共用，Mythos 5.2 未驗證）。fast mode 只開給驗證計畫內的組織（發佈文）。
- **資安分工**：
  - 找漏洞留在 Opus 5.5：Binary Exploitation Benchmark 的漏洞辨識 Mythos 5.2 跟 Opus 5.5 同級（SC pdf 51）；CVE Rediscovery 只看第一份報告時，Mythos 5.2 對 Opus 的領先從 8.3 分縮到 2.6 分（SC pdf 253）。
  - exploit 開發與多階段攻防演練，經 Stan 同意後上 Mythos 5.2，門檻跟 Fable 一樣：control-flow hijack 148 對 Opus 112（SC pdf 51）；CyScenarioBench 76.3% 對 67.6%（SC pdf 50）。都是 safeguards 關閉的數字。
  - 編譯後 binary 找漏洞：一般版 Fable 5.2 照樣擋（SC pdf 53）；Mythos 5.2 在這件事放寬多少，card 與文件沒寫，查不到。
- 能力結論跟 Fable 5.2 相同，上面 Fable 5.2 的防護全部適用。

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
2. **high 才是 Sonnet 最划算的一檔**：官方說「complements Opus 5.5 best when running at lower effort settings… At higher settings, it can perform comparably at a similar cost」。CursorBench 上 Sonnet high 只要 Opus medium 成本的 41%，AA v5.0.1 上 67%（1.64 對 2.45 美元）；要到 xhigh 才跟 Opus medium 同分同價。所以 Sonnet 開 high；xhigh 用在 fan-out，目的是吃 Sonnet 自己的週上限、不搶 Opus 額度。xhigh fan-out 派工單附官方「做完就停」段（SKILL.md 硬規則 15）。逐檔數字在 `effort-evidence.md`。
3. **不選它**：開放式、長程、要持續判斷的活（官方原話：最難的長程工作 Opus 比較好）；開到 xhigh 還過不了的任務（換 Opus 5.5 @ high，不開 Sonnet max）。
4. **max 不當起點**：發佈文腳註說 max 較常自己跑 code-review skill、拆大量 subagent，結果逾時或改超出範圍；FrontierCode 1.1 max 46.2 < xhigh 52.1。FrontierCode 2.0 放寬範圍評分後反過來，max 42.2 > xhigh 36.5，但每 rollout 19.94 對 3.31 美元，6 倍（Cognition，2026-11-23 讀）。CursorBench max 55.5 > xhigh 53.1，成本翻倍以上。AA max 每題 10.02 美元、1884 秒。
5. **要不要從 Opus 降 Sonnet，自己量**：`/claude-api build-eval` 建評測、`/claude-api hillclimb` 調 prompt（CC v2.1.259 起）。官方案例（客服問答）：prompt 瘦身後 Sonnet 5 @ low 88.9% 每題約 1¢，贏 Opus 5.5 @ low 87.8% 每題 1.9¢。
6. 發佈文沒放 Fable 5.1；System Card 的表裡 Sonnet 5.5 幾乎全贏 Fable 5.1（Terminal-Bench 70.6 vs 55.8、GDPval 1844 vs 1735），只輸多語 GMMLU（p140）。FrontierSWE v2 上 Sonnet 5.5 61.9、Opus 5.5 62.3 幾乎同分（Fable 5.2 card SC pdf 212）。

**System Card 重點**（Claude Sonnet 5.5 System Card，2026-09-28，148 頁，全文讀過並抽查引句；「圖讀」＝從圖目測、卡片內文沒寫數字）
- **差距在寫 code 與長 context**：SWE-Bench Pro 81.3 vs Opus 5.5 89.9（p109）；ProgramBench 1M 視窗 79.7 vs 91.2（p118）。贏或平的是終端機、自動化、知識工作：AutomationBench 44.7 vs 42.5、Toolathlon 77.8 平手（p109、p134）。
- **effort**：多數評測 xhigh 最划算，max 常更差且 token 暴增；GDPval xhigh 比 max 少 67% output token（p133）。CursorBench medium 39.2 / high 47.8 / xhigh 53.1 / max 55.5（p115）。每題成本以 Cursor 2026-10-07 依調整後價格重算的版本為準：medium $0.52、high $1.20、xhigh $2.81、max $7.05，Opus 5.5 medium 52.5% / $2.91（System Card 圖上讀到的 $0.7 / $3.9 / $9.7 是調價前的舊值）。Sonnet xhigh（53.1% / $2.81）跟 Opus 5.5 medium 分數與成本都差不多；主 session 直接用 Opus，fan-out 用 Sonnet xhigh 分攤額度。
- **分類器**：bio 沿用 Opus 5 那套（比 Opus 5.5 窄，無 fallback，p10、p19）；cyber 政策同 Opus 5.5，官方明說連無害的資安任務也會多被擋（p28）；編譯後 binary 找漏洞一律不幫（p29）。API 要開發者 opt-in 才自動 fallback（p29）。多階段攻防演練 CyScenarioBench 46.1%，Opus 5.5 67.6%（Fable 5.2 card SC pdf 50），多階段資安流程不派 Sonnet fan-out。
- **Prompt injection**：Sonnet 5.5 自己回答的 5,901 個 coding 攻擊請求只被攻破 4 個，破口一樣在 fallback 到 Sonnet 5 之後（p52）；瀏覽器情境是第一個 0 成功的模型（p54）；Gray Swan 比 Opus 5.5 與 Fable 5.1 弱（p50）。**卡片沒做「使用者貼上文字」這項測試**，當作跟 Opus 5.5 一樣要防（見 `opus55-system-card.md`「使用 Opus 5.5 的對策」第 1 條）。
- **行為**：誠實指標除了閃躲都比 Sonnet 5 好；被施壓時比 Opus 5.5 誠實，但幻覺較多（p56、p65）。魯莽程度只有 Opus 5.5 嚴格更好（p65）。有會把任務卡當成授權的案例（p60）。推理文字是測過最難讀的（p72），自建監控靠讀 thinking 會比較吃力。每段 transcript 輸出 token 偏多（p84）。
- **沒測的不等於沒問題**：早停、破壞性動作專項、訓練期 reward hacking（鑽評分漏洞拿分）審查都沒重做（p58）。無人值守長任務照 Opus 5.5 的對策處理。

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
5. **觀察項**：VulcanBench 上 xhigh 22/23 題、比 high 便宜又快，AA 也 +4.8；規則仍是不開 xhigh，數據記在 `effort-evidence.md`「觀察項」。
