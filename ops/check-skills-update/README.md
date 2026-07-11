# check-skills-update — Skill 上游更新檢查（原 claude-setup / drift sweep）

Stan 的 skill 生態運維流程（2026-07-11 建，2026-07-12 遷入 stan-claude-harness 並更名）。
這裡管「skill 從上游進來」的自動化；skill/hook/agent 本體住 `~\.claude\` 各自的家。
全部東西的權威地圖見 `~\.claude\SETUP.md`。

## 這個體系的六塊拼圖（源頭真相在各自檔案，這裡是地圖）

| 拼圖 | 位置 | 管什麼 |
|---|---|---|
| 分流表（routing） | `~/.claude/skills/skill-routing/SKILL.md` | 任務命中多個重疊 skill 時用哪支；含冷藏區與變更紀錄 |
| 評估流程 | `~/.claude/skills/new-skill/SKILL.md` | 新工具怎麼評（查重→深讀→兩判→對抗複查→寫回）；評完寫回分流表＋紀錄簿 |
| 評估紀錄簿 | `~/.claude/skills/skill-routing/EVALUATIONS.md` | 每個看過的工具：判定／為什麼／**評時版本**／重評觸發；本檢查的盤點來源 |
| 上游關係政策 | `~/.claude/skills/skill-routing/SKILL.md`（政策節）＋overlay patch 檔（`~/.claude/overlays/`） | 四層收納：原樣 vendor／vendor＋overlay／自寫記來源（脫鉤 fetch 不 pull）／fork |
| 觸發／強制載入系統 | `~/.claude/hooks/skill-rules.json`＋`skill-suggest.py`（UserPromptSubmit） | 關鍵字命中→軟提醒或 🔒【強制】段；Stop hook 記真實載入供對帳 |
| **check-skills-update**（本專案） | `check/` | 每週查上游差集，雙篩後自動收錄（四硬閘門除外） |

## check-skills-update

- `check/prompt.md` — 執行指示（Claude 讀這份跑）
- `check/run-check.bat` — headless 執行器（Windows 工作排程器每週一 09:23 呼叫，任務名 `CheckSkillsUpdate`）
- `reports/` — 每次檢查的報告（`check-skills-update-<YYYY-MM-DD>.md`）＋ `last-run.log`（gitignore，只留本機）
- `backups/` — 自動套用前的現版備份（gitignore，只留本機）

手動觸發：任何 session 丟一句「跑 check-skills-update」「檢查 skills 更新」，或直接執行 bat。

**授權（Stan 2026-07-11）：通過雙篩（增量＋防投毒）的內容更新自動收錄，備份可回滾、事後報告。四類硬閘門永不自動：可執行物、新外連/信任通道、LICENSE 變更、花錢/憑證/刪除。**

## 管理指令

- 看排程：`schtasks /Query /TN "CheckSkillsUpdate"`
- 停用：`schtasks /Delete /TN "CheckSkillsUpdate" /F`
- 改頻率：刪掉重建（`/SC WEEKLY /D MON /ST 09:23` 換成想要的）
