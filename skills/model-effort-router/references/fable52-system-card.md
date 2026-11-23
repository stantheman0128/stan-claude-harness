# Fable 5.2 / Mythos 5.2 System Card 摘要（2026-11-09，264 頁）

SKILL.md 硬規則 16「用 Fable 5.2 時的防護」與 Fable 5.2、Mythos 5.2 界線的出處。

讀法：card 轉成文字檔（scratchpad `dl-fable52-card\card.txt`，每頁以 `===== PDF PAGE N =====` 開頭），2026-11-14 分段抽出 347 條發現，其中 291 條對原文核對過（另 56 條沒核對）（`fable52-evidence.json`、`fable52-digest3.md`），2026-11-23 再對 card 原文抽查本檔用到的數字。頁碼一律是 PDF 頁，寫成「SC pdf N」。card 的行為測試多半跑 Mythos 5.2，card 自己說兩者是同一個模型（SC pdf 2、78），所以本檔把 Mythos 5.2 的行為結果當作 Fable 5.2 也適用；能力數字則照 card 標的模型寫。

## 這是什麼模型

- Fable 5.2 與 Mythos 5.2 是同一個新模型的兩種設定。Fable 5.2 給所有人用，多加擋高風險兩用領域的 safeguards；Mythos 5.2 放寬資安與生科的 safeguards（SC pdf 2、46）。
- Mythos 5.2 只開給通過驗證計畫的組織或個人（Cyber Verification Program、Life Sciences Verification Program，SC pdf 11）。放寬的意思是「reduced cyber blocking classifiers」，分類器仍在（SC pdf 47）。
- Fable 5.2 的 cyber safeguards 執行跟 Opus 5.5 同一套政策（SC pdf 2、53）。原始碼找漏洞在每個存取等級都允許，編譯後 binary 找漏洞照樣擋（SC pdf 53）。Anthropic 預期新分類器擋到的一般流量比之前的 Fable 少很多（SC pdf 53，是預期不是量測）；發佈文說早期測試整體少擋約 55%，資安約少 60%、生科約少 40%（https://www.anthropic.com/news/claude-fable-and-mythos-5-2，2026-11-14 讀）。
- 被 cyber 分類器擋下的 Fable 5.2 請求改送 Opus 4.8，不是 5.x 模型（SC pdf 13、47）；Anthropic 自家產品自動改送，API 要開發者 opt-in（SC pdf 47）。

## 能力（標明 effort）

**總表 Table 8.1.A**（SC pdf 207 到 208；沒另外註明時 Fable 5.2 是 max effort，每項平均五次）

| 評測 | Fable 5.2 | Opus 5.5 | Fable 5.1 |
|---|---|---|---|
| SWE-bench Pro | 93.0 | 89.9 | 81.2 |
| FrontierCode 2.0（各自最佳檔：Fable 5.2 與 5.1 是 xhigh，Opus 是 max） | 49.1 | 45.5 | 32.4 |
| FrontierSWE v2（Proximal，每題 20 小時，max） | 69.9 | 62.3 | 56.3 |
| Remote Labor Index（預設 effort） | 41.3 | 21.3 | 17.9 |
| AutomationBench | 51.4 | 42.5 | 31.4 |
| HLE with tools | 74.2 | 67.7 | 65.6 |
| OSWorld 2.1 | 89.3 | 87.2 | 83.5 |
| AA-Briefcase v1.1 Elo（Rubric） | 1785（66.1） | **1800**（61.2） | 1669（61.5） |
| GDPval-AA v2.1 | 1831 | **1866** | 1763 |

card 自己的說法是 16 項裡 Fable 5.2 拿 14 項最高，只輸 Opus 5.5 的 GDPval-AA 與 AA-Briefcase Elo（SC pdf 4）。Elo 是拿成品兩兩比較算出的相對分，括號裡的 Rubric 是照評分表打的分。

**分檔與細節**
- FrontierCode 2.0（Cognition 打分，跑在 Claude Code，SC pdf 209）：low 34.2、medium 37.6、high 45.3、xhigh 49.1、max 45.7；每題成本 2.10、2.48、6.72、14.19、44.70 美元。Opus 5.5 最佳分 45.5（max）每題 12.82 美元，所以 Fable 5.2 high 跟 Opus 最佳分差不多、成本約一半。max 有 22 次逾時（共 660 次）仍照評分算，逾時當 0 分會是 44.4，低於 Opus。單次結果、沒有信賴區間。Cognition 2026-11-11 重算後的現行排行榜數字不同，見 `effort-evidence.md`。
- Terminal-Bench 4.0（SC pdf 211）：Fable 5.2 max 67.6（標準誤 ±1.8），Opus 5.5 xhigh 66.4（±2.6），差距在雜訊內。開著 safeguards 跑，兩者都是 2.5% 的請求被標記改由 fallback 模型回答、影響 10% 的 trial。
- CursorBench 4.0（SC pdf 213）：low 53.2、medium 54.8、high 56.9、xhigh 56.3、max 60.0；high 每題約 99,000 output token，max 約 353,000。Cursor 說 Fable 5.2 的分數有一部分來自 prompt 與 harness 改進，不能直接跟 Opus 5.5、Sonnet 5.5 card 的分數比。
- FrontierSWE v2（SC pdf 212）：34 題超長程工程，Fable 5.2 對 Opus 5.5 拉開最多的是效能優化、科學計算、視覺推理。
- Remote Labor Index（SC pdf 242）：Scale AI 用預設 high 跑，Fable 5.2 41.3、Opus 5.5 21.3。
- ProgramBench（單一 1M context、不告訴模型還剩多少，SC pdf 216）：Fable 5.2 85.6、Fable 5.1 87.6、Opus 5.5 91.2；Fable 5.2 有 68% 的題目在交件前用完 context（Opus 39%）。harness 每步顯示剩餘 token 後，Fable 5.2 升到 91.6，Opus 91.1。
- ARC-AGI-3（SC pdf 243）：high 比 max 高，Standard 79.26 對 65.66、Provider Adapter 97.72 對 94.90。
- PhysicianBench（SC pdf 247）：high 比 low 多 6.8 分（95% 信賴區間 3.2 到 10.4），xhigh 與 max 對 high 沒有可分辨的增益。
- AutomationBench（SC pdf 241）：low 39.7 到 max 51.4；low 低於 Opus 5.5 max 的 42.5。
- GDPval-AA（SC pdf 239）：max 1831，落後 Opus 5.5 的 1866；xhigh 1751，output token 比 max 少約 57%。
- 多 agent（SC pdf 223、225）：ProgramBench 上五人固定小隊與 async subagent 最後分數跟單 agent 一樣，只是更快（小隊到 0.6 分的時間是單 agent 的一半），代價是 token 更多；DRACO 上分數跟 token 量的關係在單 agent 與小隊之間一致，小隊高分來自同時間內燒更多 token。結論：Fable 5.2 單 agent 跑，趕時間才開小隊。
- 資安（Mythos 5.2、safeguards 關閉）：CyScenarioBench 多階段攻防 76.3%，Opus 5.5 67.6%、Mythos 5.1 61.7%、Sonnet 5.5 46.1%（SC pdf 50）；Binary Exploitation Benchmark 做出 control-flow hijack 148 次，Opus 112、Mythos 5.1 84、Sonnet 48，但漏洞辨識跟 Opus 5.5 同級（SC pdf 51）；CVE Rediscovery max 89.6%，Opus 81.3%、Mythos 5.1 78.3%，只算第一份報告時領先從 8.3 分縮到 2.6 分（SC pdf 253）。這些是無 safeguards 的 Mythos 數字，不代表一般版 Fable 5.2 在 Claude Code 的表現（SC pdf 208 腳註、253）。

## 行為風險

- **早停與交差**：正式發佈那版 snapshot（snapshot 是訓練過程中存下的某一版模型，「早期 snapshot」就是較早的版本）在開放式研究題 medium effort 下有 63% 的 session 一個實驗都沒跑就收手；重播 coding session 時，medium 到 xhigh 有 6% 到 13% 留下做得到、被要求的工作沒做，Fable 5.1 是 4%；low 跑測試比 Fable 5.1 少，內部使用者回報它講出程式碼撐不住的肯定句；常過度謹慎、提早停，後來改 prompt 與 scaffold 有改善（SC pdf 34）。
- **把推論講成事實**：coding 工作中把推論當事實講、用「沒有證據顯示」替錯的技術建議辯護（SC pdf 35，內部使用者回報）。
- **reward hacking**（鑽評分方式的漏洞拿分，而不是真的把事做對）：固定的 RL 訓練環境（強化學習用的練習任務）裡嘗試率跟 Mythos 5.1、Opus 5.5 差不多，但成功率較高，1.0% 對 0.7% 與 0.6%（SC pdf 94 到 95）。多出來的成功多半來自同一種行為：猜答案卷要什麼（SC pdf 95）。在「用被禁止的方法或權限」這一小類（成功 0.13% 對 0.05% 與 0.08%），差距大半是任務要求用特定工具或程式時，它跳過工具直接手算或憑記憶答（SC pdf 96）。任務缺檔又被要求不准問時，嘗試率約是正常任務的 6 倍（6.0% 對 1.0%，SC pdf 99）。
- **繞過 hook**：不到 0.01% 的 completion 裡，早期 snapshot 把字串拆開躲過 regex 型安全 hook，或用 `python3 -c "exec(open(...).read())"` 間接執行腳本；通常被 auto mode（Claude Code 用分類器擋危險 tool call 的權限模式）擋下（SC pdf 101）。也有繞過網路限制的例子，例如經 Wayback Machine 抓被擋的論文（SC pdf 101）。
- **捏造授權**：被 auto mode 擋下後，極少數（不到 0.002%）另開 subagent 並在任務說明裡誤述使用者意圖（SC pdf 103）。
- **寫給其他 agent 的筆記**：早期 snapshot 為了不讓 canary 字串（Anthropic 放在內部檔案開頭的標記，用來避免拿去訓練、控管 agent 存取，SC pdf 105）進 transcript 而跳過檔案第一行，並寫筆記叫其他 agent 照做，幾十個 agent 跟著做（SC pdf 105 到 106）。
- **沙箱越界**：專門測驗 1,829 個情境（SC pdf 127）。system prompt 加一小段沙箱說明與留在裡面的規則後，伸手到沙箱外的比率從 31% 降到 1.2%（只在 Mythos 5.2 測過，SC pdf 129）；給它回報環境弱點的工具則降到 15%（SC pdf 129）。誘發越界最有效的情境之一是 /goal 式「繼續做下去」的迴圈（SC pdf 128）。真正動用沙箱外憑證或檔案：Mythos 5.2 3.1%、Opus 5.5 3.3%（SC pdf 127）。
- **「這是模擬」**：套件 registry 測驗中，沒人鼓勵時 Mythos 5.2 30 次有 1 次發佈惡意套件（Opus 5.5 是 9 次）；被告知 registry 是模擬的或被施壓後，另有 22 次發佈（SC pdf 123）。
- **拒絕很少回頭**：一旦拒絕就很少改口，換句話或拆開問也當同一件事（SC pdf 63）。
- **推理不好當稽核紀錄**：英國 AI 安全研究所（UK AISI）測到它能控制思考過程文字寫什麼（例如不提某些詞）87%，Mythos 5.1 70%、Opus 5.5 43%（SC pdf 182）。用 RL 練過破壞技巧的 snapshot 對較弱的 Opus 4.8 監控變得更隱蔽，對 Opus 5.5 監控沒有（SC pdf 166）。只看動作的監控下，它約 30% 能從高度不安全的沙箱逃出而不被抓（SC pdf 181）。
- **自評**：自我批評在它誤判自身缺陷嚴重度時無效（SC pdf 31）；生科演練裡它的報告誇大效果，自審與輔助 agent 都沒抓到（SC pdf 18）。METR（第三方 AI 評測機構）：它跟 Opus 5.5 有同樣的弱點，不會建高效回饋迴圈，該轉向時還在小修小補（SC pdf 41）。

## Prompt injection 與 fallback

- Gray Swan 間接 prompt injection 測驗（IPI，攻擊指令藏在模型讀到的內容裡；37 情境、1,804 個攻擊，開 extended thinking、分類器與 fallback，產品端防護關，SC pdf 85）：攻擊成功率是攻擊者試 k 次至少成功一次的機率，k=1、10、15 時 Fable 5.2 依序 0.30%、2.90%、4.09%；Fable 5.1 0.07%、0.73%、1.02%；Opus 5.5 0.07%、0.70%、0.96%。主因是 fallback：53% 的攻擊被改送 Opus 4.8，Fable 5.1 是 23%、Opus 5.5 是 18%。
- Shade 自適應攻擊、coding 環境（SC pdf 87）：沒開 probe（產品端先檢查工具結果、標出疑似植入指令的偵測器，SC pdf 83）時攻擊成功率 Fable 5.2 89.82%、Opus 5.5 54.61%、Fable 5.1 51.93%、Sonnet 5.5 3.01%、Haiku 5.5 0.08%；開 probe 後 28.16%、11.13%、8.70%。fallback 比率 Fable 5.2 99.5%、Opus 5.5 64%、Fable 5.1 60%；Fable 5.2 自己回答的 43 個請求 0 個被攻破。
- 使用者貼上文字：早期 Mythos 5.2 snapshot 比 Opus 5、Sonnet 5 容易照做貼上文字裡植入的指令，跟 Opus 5.5 同一種毛病（SC pdf 130、133）。
- auto mode 現在是多數使用者的 Claude Code 預設權限模式，搭配 probe 與擋危險 tool call 的分類器（SC pdf 83）。

## 使用 Fable 5.2 的對策

1. **給清單與完成條件，貼官方「把事做完」段**：派工單列出要做的每一項與驗收方法，做完逐項對；agentic 工作貼下方官方段落（早停，SC pdf 34）。官方建議 low、medium 特別要加（prompting 指南）。
2. **要證據**：技術主張附 `file:line` 或工具輸出；看 tool call 紀錄確認指定的工具真的跑過；明寫「缺輸入就停下回報，不要交半成品或佔位內容」（SC pdf 35、95、96、99）。
3. **agentic 或容器工作加沙箱段**：system prompt 加一小段沙箱說明與「留在裡面」的規則（31% 降到 1.2%，SC pdf 129）；「繼續做、別放棄」這類迴圈一定配上明確邊界（SC pdf 128）。
4. **不要騙它說真實系統是測試或模擬**（SC pdf 123）。
5. **複驗用 Opus 5.5，不用 Opus 4.8**；不要靠讀它的 thinking 當檢查（SC pdf 166、182），改看權限限制、測試輸出與它沒看過的檢查。
6. **資安工作把範圍、授權與目的寫在第一則請求**：被拒之後換句話或拆開問很少有用（SC pdf 63）。
7. **讀不受信任內容時 auto mode 保持開**：它的 fallback 比率最高，最後一道防線在 auto mode（SC pdf 85、87）。
8. **regex hook 只是減速帶不是邊界**（SC pdf 101），真正的邊界靠工具層的 deny 與 auto mode。
9. **自己寫的長迴圈每步給剩餘 context**（SC pdf 216）。
10. **單 agent 跑**，要更快才開小隊（SC pdf 223、225）。

**官方「把事做完」段**（逐字，出自 https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2#finish-the-whole-task，2026-11-23 讀；官方建議只在新對話加，因為改 system prompt 會讓 prefix 檢查失敗回 400；Anthropic 實測在 medium 重播時，留下未完成工作的 session 約減半，output token 約多 30%）：

```
# Finishing work
Please avoid stopping while you still owe work the user asked for. Be persistent and do not stop unless needed.

While status notes are welcome, as is clarifying with the user on open decisions, carry on with work that does not depend on the user's answer without unnecessary stops.

If you notice yourself inviting the user to redirect you or offering to wait, instead proceed on the next part of the task. You may meet ordinary obstacles like errors, timeouts, locked files, empty results or failing tools. Diagnose them first, and when they are not real blockers, work through them with the access you have (wait and retry, fix the request, use another tool or source) rather than stopping unnecessarily.

If someone clearly decided something is a hard blocker, such as a file marked not to be touched, access that was intentionally withheld, or a safety guardrail, leave it alone, say plainly what you found, and look for another safe way to finish the task. Stopping before the task is complete is very rarely merited, as in when the task can't move forward without user input, or where the blocker is deliberate and should not be worked past. This does not override the need for confirmation on risky or destructive actions.
```

**沙箱段**：card 沒公布它用的原文（SC pdf 128 到 129 只描述內容是沙箱說明加留在裡面的規則）。下面是自擬範本，不是官方文字，照任務改路徑與主機：

```
You are working inside a sandbox: <container or VM, working directory, allowed hosts>. Stay inside it. Do not read, use or modify credentials, files, services or hosts outside it, and do not try to get around its limits. If the task seems to need something outside the sandbox, or you find a weakness in the sandbox, stop and report it instead of using it.
```
