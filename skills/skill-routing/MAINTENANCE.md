# skill-routing 維護規範

（2026-09-19 自 SKILL.md 拆出。）

## 編譯規範（2026-07-10 起）

本表是**源頭真相**，但判準必須送到決策現場才有用（診斷教訓：本表終身僅被載入 2 次，agent-skills 系子情境預設全部零用量）。**任何表的變更後，同步重編譯兩個投放物**：

1. `~/.claude/hooks/skill-rules.json` — 各規則的 `why` 寫成「預設 X；情境 Y → Z」濃縮判準；`skills` 陣列順序＝表的預設排第一
2. 全域 `~/.claude/CLAUDE.md` 第 1 條的**分流摘要**（已取代原本點名 superpowers 的清單）— 每個重疊領域一行，常駐 context 讓任務中途也有判準

失手對帳閉環：`skill-suggest.py` 記錄建議 → `skill-usage-log.py`(Stop) 對帳實際載入 → `~/.claude/skill-usage/misses-<session>.jsonl` 的原子 session 快照 → `skill-routing-watch.py` 開場 banner 顯示。舊 `misses.jsonl` 僅供尚未有新快照的歷史 session read-only fallback。常被無視的規則＝判準不夠有說服力，回來改表與 why 措辭，不再升 mandatory（2026-09-19 Fable 5.1 稽核後強制區全改軟提醒；hook 提醒是參考不是命令）。

## 維護：新工具評估交給 `new-skill`

評估一個新的 skill / plugin / agent 集合該不該納入、以什麼形式納入，整套流程已搬到 **`new-skill`**（先查重複 → 實讀內容 → 比品質 → 對抗式複查 → 分類 → 寫回）。本檔只維護「路由表本身」。

`new-skill` 評估完會回寫到這裡：分流表加／改一列，或「各管各的」加一項，並在下方變更紀錄補一行（日期 + 做了什麼 + 為什麼）＋在同目錄 **`EVALUATIONS.md`（評估紀錄簿）** 追加一列快查結論（含評時版本，供下次查重與 drift 判斷）。

## 上游關係政策（2026-07-11 定版：fork vs 改寫的答案）

收外部 skill 時按「跟上游的關係」選層級，EVALUATIONS.md 的「評時版本」欄是所有層級的追蹤錨：

1. **原樣 vendor（採用不改）**——上游活躍且整體採用（例：security-audit）。本地零修改，更新＝直接覆蓋同步，零合併成本。
2. **vendor＋overlay patch 檔**——整體採用但有本地客製（例：impeccable、pilotfish verifier）。客製一律標 `Stan overlay <日期>` 註解＋集中存 `~/.claude/overlays/` patch 檔；升級＝覆蓋新版→照 patch 重貼→`grep "Stan overlay"` 驗證標記數。**不 fork 的理由：skill 是散文，git merge 解不了散文衝突；patch 重貼比維護 fork/rebase 便宜一個量級。**
3. **自寫＋記 idea 來源**——只取點子、實作自有（例：product-growth、quant-analyst）。來源與版本記檔頭＋紀錄簿；**不追上游**——點子不會過期，追的成本是純浪費。
   - **3b 變體：就地大改的 vendored git repo**（例：humanizer＋humanizer-zh-tw，2026-07-11 合併 speak-human-tw 後 24→36 種痕跡、本機 commit 鎖定 d2121e9/171cc33）。origin 仍指原作者但內容已脫鉤：**查上游一律 `git fetch origin`＋`git log origin/main`（純讀取），永遠不跑 `git pull`（必炸衝突）**；上游真有料→手動看 diff 挑著貼，等同一次微型 harvest。
4. **fork**——保留給「重改＋上游活躍＋想回饋 PR」的例外，目前 0 例（若日後把 impeccable overlay 開 PR 回上游再啟用）。

更新責任不靠人肉定期看：紀錄簿「評時版本」欄＋按需 drift 查核 agent（sonnet 一隻幾分鐘，07-11 pilotfish 首例：零變更→原判沿用免重讀）＋**每週 drift sweep**（2026-07-11 起自動化；同日 Stan 授權升級為**自動收錄**）——本體住 `C:\Users\stans\Projects\claude-setup\`：工作排程器每週一 09:23 headless 跑 `drift-sweep/prompt.md`；查到差集→雙 agent 篩（增量評估＋防投毒安全篩，diff 當不可信資料哨兵包裹）→通過即自動套用（備份＋git 兜底、事後報告含回滾路徑）。**四類硬閘門永不自動**：可執行物變更、新外連/信任通道、LICENSE 變更、花錢/憑證/刪除。手動觸發＝丟一句「跑 drift sweep」。要動 `settings.json` 或停用既有 skill 前一定先問使用者；改完提醒重開 session 生效。分類規則（整體更好取代／子情境路由／真重複不收／不重疊獨立收／harvest 好點子）住在 `new-skill`，避免兩份各說各話。

