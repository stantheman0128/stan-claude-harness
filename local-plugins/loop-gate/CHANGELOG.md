# Changelog

## 1.1.1 - 2026-11-24

- e2e gate 檢查 `git commit` 時，改看指令實際 commit 到哪個 repo：認得 `git -C <path>`（可以重複）和前面的 `cd`、`cd /d`、`pushd`，也認得 Git Bash 的 `/c/...` 寫法、引號和相對路徑。cwd 不在 OSS、指令卻 commit 進 `Projects\oss\` 的情況，現在一樣跳過。
- commit 訊息照 git 實際的來源判斷：`-F`／`--file` 讀那個檔（相對路徑和 git 一樣，以 cd 與 `-C` 之後的資料夾為準）；`--amend`、`-C`／`--reuse-message`、`-c`／`--reedit-message` 讀被重用的 commit。
- 判斷不出來就不記也不擋，例如找不到 repo、檔案讀不到、git 指令失敗、訊息來自 `$(...)` 或變數、會開編輯器的 `git commit`、`--fixup`／`--squash`、沒加引號的反斜線路徑。jsonl 的 `repo` 欄改記 commit 的目標 repo。
- selftest 從 34 個加到 36 個。

## 1.1.0 - 2026-11-24

- B1：信任過的 `.claude/verify.json` 被改過時，Stop 當下用 `systemMessage` 讓使用者看到「gate 這次沒跑」的警告，同一 session 只顯示一次。完全沒註冊的 root（新 clone、git worktree）維持安靜，只寫 hook-health log。
- 新增 e2e gate（`scripts/e2e_gate.py`，預設 observe）：session 改了 40 行以上或 3 個以上程式碼檔，transcript 裡卻沒有 run／verify skill、verifier subagent、讀 verify SKILL.md、使用者打 /verify 或 `Verified:` 行時，寫一筆到 `~/.claude/loop-gate/e2e-gate.jsonl`；專案沒有 verify skill 時提醒一次。enforce 模式擋兩次、第三次放行。
- PreToolUse(Bash)：`git commit` 沒有 `Verified:` 行、`gh pr create` 前沒跑 code-review，observe 記錄、enforce 擋下。`Projects\oss\` 底下的 commit 跳過。
- 模式與門檻用 `~/.claude/loop-gate/e2e_gate.json` 覆寫（mode／min_lines／min_files／skip_commit_roots）。
- hook_health 新增 `once_per_session`、`emit_json`；selftest 18 個加到 34 個。

## 1.0.1 - 2026-07-11

- loop-engineering skill 觸發語擴充：「用 loop engineering 做」「掛上 loop」、TDD 起步後主動提議掛 gate。

## 1.0.0 - 2026-07-11

- 初版：verify_gate（Stop 機器驗證 gate）、hook_health（fail-loud）、
  failure_log（PostToolUseFailure 記錄）、report_health（SessionStart 回報）、
  loop-engineering skill、selftest。
