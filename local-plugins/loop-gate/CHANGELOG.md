# Changelog

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
