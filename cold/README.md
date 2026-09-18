# 冷藏區（2026-09-18 Fable 5.1 稽核後移入）

這裡的 skill 與 agent 不會被 Claude Code 載入，也不進 system prompt 的清單。
移入依據：`~/.claude/skill-usage/` 287 個 session 內 0 次使用，且內容是通用方法論
或 Solana/crypto 專案包，模型本身已涵蓋或目前沒有對應專案。

還原單一 skill：
    mv ~/.claude/cold/skills/<name> ~/.claude/skills/<name>
還原單一 agent：
    mv ~/.claude/cold/agents/<name>.md ~/.claude/agents/<name>.md
全部還原：
    git -C ~/.claude revert <本次 commit>
