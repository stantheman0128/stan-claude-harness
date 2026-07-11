# loop-gate plugin 設計 spec（2026-07-11）

## 目的

把 loop engineering 的兩件核心做成跨專案通用的 Claude Code plugin：

1. **收工驗證不經過模型**：Claude 說「做完了」之前，由 hook 親自跑該專案宣告的驗證命令，紅燈就擋下收工並把真實錯誤退回，杜絕四種假全綠（沒跑、誤讀、跑錯、謊報）。
2. **harness 自我改進的安全閥**：hook 改動先過 selftest 才啟用；hook 失效必須大聲（fail loud），不准靜默退化。

理論依據：arXiv 2603.23420（Bilevel Autoresearch）的 validate-and-revert 與 silent-fallback 教訓；
LangChain 四層 loop 模型的 Loop 2（hook 強制驗證 gate）。

## 形態

Local plugin `loop-gate`，掛在 `stan-local-plugins` directory marketplace
（`C:\Users\stans\Projects\project-sweep-plugin\loop-gate\`）。
plugin 啟用後 hooks 自動 merge 進全域 hooks，不改 `~/.claude/settings.json` 的 hooks 段。

## 目錄結構

```
loop-gate/
├── .claude-plugin/plugin.json      # name=loop-gate, version=1.0.0
├── CHANGELOG.md
├── hooks/hooks.json                # Stop + PostToolUseFailure + SessionStart
├── scripts/
│   ├── verify_gate.py              # Stop 驗證 gate（核心）
│   ├── hook_health.py              # fail-loud 共用函式庫
│   ├── report_health.py            # SessionStart 健康回報
│   ├── failure_log.py              # PostToolUseFailure 記錄器
│   └── selftest/
│       ├── run.py                  # selftest runner
│       └── fixtures/               # 假 event JSON
└── skills/loop-engineering/SKILL.md
```

## 元件規格

### 1. verify_gate.py（Stop hook）

**輸入**：stdin 的 Stop event JSON（欄位：`session_id`、`stop_hook_active`、`cwd`、`transcript_path`）；
環境變數 `CLAUDE_PROJECT_DIR`（優先）或 event 的 `cwd` 當專案根。

**每專案 manifest**：`<專案根>/.claude/verify.json`

```json
{
  "command": "npm test --silent",     // 必填。驗證命令，shell 執行
  "timeoutSec": 300,                  // 選填，預設 300
  "cwd": "colonist-stats-tracker"     // 選填，相對專案根；monorepo 用
}
```

**決策表**（依序判定，命中即停）：

| # | 條件 | 動作 | 理由 |
|---|------|------|------|
| 1 | `stop_hook_active == true` | exit 0 | 防無限迴圈（官方欄位） |
| 2 | manifest 不存在或解析失敗 | exit 0（解析失敗另記 health log） | opt-in：沒宣告的專案零干擾 |
| 3 | manifest **未通過信任註冊**（見安全模型） | exit 0 + health log 記 untrusted-manifest | 防惡意 repo 夾帶 manifest 的 drive-by 執行 |
| 4 | evidence 存在、fingerprint 相同、result ∈ {green, assumed-baseline} | exit 0 | 快路徑：本狀態已驗過（或被視為可信基線），不重跑 |
| 5 | evidence 不存在、且 git 工作區乾淨 | 寫 baseline evidence、exit 0 | 純問答 session 不冷跑全套測試；gate 的目標是「這個 session 改了東西卻沒證明」 |
| 6 | 其他 | 跑 verify 命令 | |

**Fingerprint**（狀態指紋，判斷「上次驗證後程式碼有沒有變」）：
`sha1(git rev-parse HEAD + git status --porcelain 輸出 + git diff HEAD 輸出)`。
兩個實作上必要的修正（實作期實證發現，2026-07-11）：
(a) 用**完整 diff** 而非 `--stat`——`--stat` 只記行數，同行數的改動會產生相同指紋、快路徑會漏驗；
(b) status/diff 輸出要先**濾掉 `loop-gate-evidence.json` 自身**再 hash，否則沒把 evidence
    加進 .gitignore 的專案，寫入 evidence 這個動作本身就會讓指紋永遠對不上、快路徑永久失效。
非 git repo → fingerprint = null，等同永遠不相同（每次 stop 都跑；opt-in 專案自己承擔）。

**Evidence 檔**：`<專案根>/.claude/loop-gate-evidence.json`
`{"fingerprint": "...", "result": "green|assumed-baseline", "ts": "...", "command": "..."}`。
部署時把它加進該專案 `.gitignore`。

**安全模型（信任註冊）**：manifest 的 `command` 是任意 shell 字串，跟 package.json scripts 同級的
「專案擁有者信任」模型；但 Stop hook 是**自動**觸發的，若不設防，惡意 repo 只要夾帶
`.claude/verify.json` 就能在 Stan 開 session 閒逛時執行任意命令（等同 2026 年那批 settings.json
hook RCE CVE 的向量）。因此：

- 信任註冊表 `~/.claude/loop-gate/trusted.json`：`{ "<專案根絕對路徑>": "<verify.json 內容的 sha256>" }`。
- gate 執行前比對：專案根不在表中、或 manifest 內容 hash 不符 → 跳過（exit 0）+ health log 記
  `untrusted-manifest`（SessionStart 回報會浮出，Stan 就知道要跑 init 重新信任）。
- 註冊/更新只走 skill 的 init 流程（人在場核可 command 內容後寫入 hash）。

**跑命令**：`subprocess.run(command, shell=True, cwd=專案根/manifest.cwd, timeout=timeoutSec, capture_output=True)`。
`shell=True` 是刻意的：verify 命令本來就是 shell 語句（`npm test --silent` 在 Windows 需經 shell 解析
.cmd shim），且輸入來源已被信任註冊表限定為「Stan 本人核可過的字串」，不存在未信任輸入拼接。

- **綠**（exit 0）→ 寫 evidence（green）、清空 strikes、exit 0。
- **紅** → strikes + 1：
  - strikes < 3：stderr 輸出「[loop-gate] 驗證未過（第 N/3 次），修好才能收工。命令：...。輸出尾段：」+ 最後 40 行，**exit 2**（擋下收工，stderr 退回給模型）。
  - strikes ≥ 3：stderr 輸出「[loop-gate] 連續 3 次未過，放行但標記失敗。請人工介入。」，**exit 0**（fail-open，比官方內建 8 次 cap 保守）。
- **timeout / 例外** → 記 health log、exit 0（fail-open + loud：壞掉的 gate 不准把 Stan 鎖死）。

**Strikes 狀態**：`~/.claude/loop-gate/strikes/<session_id>.json`，綠燈或放行後歸零/刪除。

### 2. hook_health.py（fail-loud 共用函式庫）

- `guard(hook_name, main_fn)`：包住 hook 主邏輯；捕到未預期例外 →
  append 一行 JSON 到 `~/.claude/hook-health.log`（`{ts, hook, error, traceback 摘要}`），exit 0。
- 原則：**gate 類 hook 失效 = fail-open + 大聲記錄**，絕不靜默。
- log 超過 1MB 自動 rotate（保留一份 .old）。

### 3. report_health.py（SessionStart，matcher=startup）

讀 `hook-health.log` 近 24 小時的失敗 → 有就 stdout 一行
`[loop-gate] ⚠ 過去 24h 有 N 次 hook 失敗（最近：<hook> <error>），詳見 ~/.claude/hook-health.log`；
沒有就不輸出（零噪音）。stdout 會進 session context，讓下一個 session 的 Claude 主動告知 Stan。

### 4. failure_log.py（PostToolUseFailure）

append `{ts, session_id, tool_name, error 前 500 字}` 到
`~/.claude/loop-gate/tool-failures.jsonl`（>2MB rotate）。
用途：當 hookify conversation-analyzer 與 Loop 4 檢討的素材。

### 5. hooks/hooks.json

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command",
          "command": "py \"${CLAUDE_PLUGIN_ROOT}/scripts/verify_gate.py\"",
          "timeout": 420 } ] } ],
    "PostToolUseFailure": [
      { "hooks": [ { "type": "command",
          "command": "py \"${CLAUDE_PLUGIN_ROOT}/scripts/failure_log.py\"",
          "timeout": 10 } ] } ],
    "SessionStart": [
      { "matcher": "startup",
        "hooks": [ { "type": "command",
          "command": "py \"${CLAUDE_PLUGIN_ROOT}/scripts/report_health.py\"",
          "timeout": 10 } ] } ]
  }
}
```

Windows 注意：shell form（走 Git Bash）+ `py` launcher，是現有 7 支 hook 已驗證的寫法。

### 6. skills/loop-engineering/SKILL.md（薄 skill）

三個流程：

1. **init**：幫任意專案建 `.claude/verify.json`（問清 command/timeoutSec/cwd）、把 evidence 檔加進 .gitignore、跑一次 gate selftest 確認掛上。
2. **Loop 4 檢討流程**：被糾正後 → 寫 `tasks/lessons.md` → 丟 `hookify:conversation-analyzer`
   判斷「這個錯能不能變成機器攔截的規則」→ 生成的 hook 規則**必經人工審核**才啟用
   （安全底線：hooks 以完整 shell 權限執行，2026 年已有多個 settings.json hook RCE CVE）。
3. **harness 改動檢查表（validate-and-revert）**：改任何 hook →
   `py scripts/selftest/run.py` 全綠 → 才啟用；壞了 `git checkout` 還原。

### 7. selftest（TDD 的測試基礎設施）

`run.py`：對 scripts 以 subprocess 餵 fixtures、斷言 exit code + stderr/stdout 內容 + 副作用檔案。
獨立 temp 目錄跑，**不碰真實的 ~/.claude**（用環境變數覆寫 state/log 路徑，如 `LOOP_GATE_HOME`）。

必備案例（verify_gate）：

| 案例 | 預期 |
|---|---|
| stop_hook_active=true | exit 0，不跑命令 |
| 無 manifest | exit 0 |
| manifest 壞 JSON | exit 0 + health log 有記錄 |
| 綠燈命令 | exit 0 + evidence 寫入 green |
| 紅燈命令（第 1、2 次） | exit 2 + stderr 含輸出尾段 |
| 紅燈第 3 次 | exit 0 + stderr 含放行警告 |
| 綠燈後未改碼再 stop | exit 0 且**不重跑命令**（快路徑，用 marker 檔證明沒執行） |
| 改碼後 stop | 重跑命令 |
| 乾淨工作區 + 無 evidence | exit 0 寫 baseline，不跑命令 |
| 非 git 目錄 | 每次都跑命令 |
| 命令 timeout | exit 0 + health log |
| manifest 未註冊信任 | exit 0，不跑命令，health log 記 untrusted-manifest |
| manifest 內容變更後未重新註冊 | 同上（hash 不符） |

hook_health / failure_log / report_health 各配 2-3 個基本案例。

## v1 明確不做（YAGNI）

agent-type hook 裁判（官方標 experimental）、PostToolUse lint/typecheck（等有 TS 專案）、
自動改 CLAUDE.md 的全自動 Loop 4、TDD Guard / SkillClaw 整合、
把現有 7 支全域 hook 收編進 hook_health（v1.1 再逐支做）。

## 部署步驟（實作完成後）

1. `claude plugin validate` 過。
2. marketplace.json 加 loop-gate entry（version 1.0.0）。
3. `~/.claude/settings.json` 的 enabledPlugins 加 `"loop-gate@stan-local-plugins": true`。
4. 試點：`chrome-extensions/.claude/verify.json`（command=`npm test --silent`，
   evidence 進 .gitignore；monorepo 注意：只 add 指定路徑），並把該 manifest
   註冊進 `~/.claude/loop-gate/trusted.json`（信任註冊）。
5. 重開 session 生效；用 selftest + 手動觸發驗證。

## 版本紀律

plugin 自帶 CHANGELOG.md，每個元件完成 = 一個 commit（marketplace repo 內用明確路徑 add）。
