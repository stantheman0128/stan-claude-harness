---
name: loop-engineering
description: loop-gate 驗證 gate 的管理流程。主動使用本 skill 當使用者說「用 loop engineering 做」「掛上 loop」「幫某專案掛驗證 gate」「init verify manifest」「loop-gate 設定」，或新專案 TDD 起步後測試套件可跑（此時主動提議掛 gate），或被使用者糾正後要走 Loop 4 檢討（lessons.md + hookify），或要改任何 hook / harness 設定前需要 validate-and-revert 檢查表時。
---

# loop-engineering：驗證 gate 與自我改進迴圈的管理

前置知識：loop-gate plugin 的 Stop hook 會在收工前讀
`<專案根>/.claude/verify.json`（manifest），由機器跑驗證命令決定能不能收工。
設計細節見 plugin repo 的 `docs/specs/2026-07-11-loop-gate-design.md`。

## 流程一：幫專案掛上驗證 gate（init）

1. 問清（或從專案推斷後跟使用者確認）三件事：
   - `command`：驗證命令（如 `npm test --silent`）。要能在專案根以 shell 執行、exit 0 = 綠。
   - `timeoutSec`：預設 300，全套測試要跑多久就設多少（再加緩衝）。
   - `cwd`：monorepo 才需要，相對專案根。
2. 寫 `<專案根>/.claude/verify.json`。
3. 把 `.claude/loop-gate-evidence.json` 加進該專案 `.gitignore`（沒加的話快路徑仍可運作，但 evidence 會出現在 git status 干擾使用者）。
4. **人工確認 command 內容安全後**，執行信任註冊：
   `py "<plugin root>/scripts/trust_manifest.py" "<專案根絕對路徑>"`
   （何時執行：manifest 初建與每次內容變更後。執行後：下一次 Stop 即生效。）
5. 驗收：故意讓一個測試紅燈、觸發 Stop，確認被擋且 stderr 有輸出尾段；修好再 Stop，確認放行。

## 流程二：Loop 4 檢討（被使用者糾正之後）

1. 照慣例把教訓寫進 `tasks/lessons.md`。
2. 多做一步：問「這個錯能不能變成機器攔截的規則？」能的話丟
   `hookify:conversation-analyzer` 產生 hook 規則草稿。
3. **鐵律：自動生成的 hook 規則必經人工審核才啟用**——hooks 以完整
   shell 權限執行，2026 年已有多起經 settings.json hooks 的 RCE CVE。
4. 素材來源：`~/.claude/loop-gate/tool-failures.jsonl`（工具失敗記錄）、
   `~/.claude/hook-health.log`（hook 自身失敗）。

## 流程三：harness 改動檢查表（validate-and-revert）

改任何 hook script / hooks.json / manifest 之前與之後：

1. 跑 selftest：`py "<plugin root>/scripts/selftest/run.py"`，必須全綠。
2. 改 hooks.json 後跑 `claude plugin validate <plugin root>`。
3. 壞了就 `git checkout` 還原（plugin repo 有完整版控），不要帶病上線。
4. hook 行為改動要 bump plugin version + CHANGELOG（一功能一版號）。
5. 改完 hooks 要重開 session 才生效（plugin hooks 在 session 啟動時載入）。
