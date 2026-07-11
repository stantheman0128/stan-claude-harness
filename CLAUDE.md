# Claude Code Workflow Orchestration

## Workflow Orchestration

### 1. Plan Node Default → 強制走工作流 skill（Stan 指令 2026-07-02；分流判準 2026-07-10 併入，取代原點名清單）
- **任何非瑣碎任務（3+ 步 / 有架構決策）動手前，你【必須】先載入對應的工作流 skill，不得只在腦中或散文裡規劃就開工。選哪支照下面的分流摘要（格式：預設；情境 → 改用）：**
  - 目標/作法不明 → `superpowers:brainstorming`；整個功能請 Claude 主導 → `guided-dev`
  - 規劃/spec → 預設 `guided-dev`；要可執行 runbook → `superpowers:writing-plans`；拆可驗收小任務 → `agent-skills:planning-and-task-breakdown`；正式規格 → `agent-skills:spec-driven-development`
  - 寫測試/TDD → 預設 `superpowers:test-driven-development`；選測試種類/金字塔 → `agent-skills:test-driven-development`
  - 修 bug → 預設 `agent-skills:debugging-and-error-recovery`（快速 web bug）；flaky/效能回歸/多元件 → `diagnosing-bugs`（先建紅燈迴圈）；連 3 次修不好 → `superpowers:systematic-debugging`
  - 宣稱完成前 → `superpowers:verification-before-completion`
  - code review → 內建 `/code-review`；流程總檢查表 → `agent-skills:code-review-and-quality`
  - 程式簡化 → `agent-skills:code-simplification`
  - 效能 → `agent-skills:performance-optimization`；線上單頁深度稽核 → `cloudflare:web-perf`
  - 前端視覺/UI → `impeccable`；元件架構/React 寫法 → `agent-skills:frontend-ui-engineering`
  - API/介面/seam 設計 → `agent-skills:api-and-interface-design`
  - 安全深度稽核 → `security-audit`（吃 token）；設計期威脅建模 → `agent-skills:security-and-hardening`
  - git → `agent-skills:git-workflow-and-versioning`；worktree/收尾分支 → `superpowers:using-git-worktrees` / `finishing-a-development-branch`
  - 逼問計畫 → `grilling`；還沒計畫先挖意圖 → `agent-skills:interview-me`
  - 完整判準、冷藏區（已停用 skill 清單與復原法）→ 載 `skill-routing`
- 載入時在回覆標「⚙️ Using <skill>」（配合第 7 條 live trace），結尾對帳單也要出現。
- **不准默默跳過。** 若判定某任務確實不需要（純問答／單行小改／領域 skill 已自帶規劃階段，如 impeccable 的 `shape`），回覆**第一行**必須明講豁免理由。UserPromptSubmit hook 命中時會注入 🔒【強制】段，那代表 Stan 的長期指令、優先級等同使用者直接要求。
- 領域 skill 內建規劃階段時，載該領域 skill 即可，不必再疊通用規劃 skill（避免流程表演）。
- 出事就 STOP 重新規劃、別硬推；plan mode 也用在驗證，不只建構；規劃前寫清楚 spec 降低歧義。

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution
- 派工規格一次到位：goal、constraints、done-criteria、相關路徑、為什麼——讓 subagent 不用回頭問（harvest 自 pilotfish 2026-07-10）
- **派工先選角色**（pilotfish v1.1.2 分工制，2026-07-11 Stan 拍板啟用）：查找/盤點事實→`scout`（haiku 唯讀）；已規格化的機械活（照 spec 改檔/照慣例寫測試/批次改名）→`mech-executor`（sonnet）；要判斷的實作→`executor`（opus）；安全敏感實作（auth/秘鑰/驗證/加密）→`security-executor`（opus）；完工複驗→`verifier`（鎖寫入，派工單絕不含修復指令）。主 session 只做規劃、裁決、整合。大規模批次 fan-out 仍照 [[feedback-subagent-model-policy]]（sonnet 5）。廣域搜索用內建 `Explore`（pilotfish 同名模板已跳過不裝）

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness
- 非平凡任務的完成驗證，可派全新 context 的 subagent 獨立複驗，不靠原 context 自我驗證（harvest 自 pilotfish 2026-07-10）。2026-07-11 起已裝其原版 `verifier` agent（opus、鎖 Write/Edit、只回 CONFIRMED/REFUTED）——複驗優先派它：`subagent_type: verifier`。**派工單絕不含「發現問題順便修」類指令**（07-11 壓力實測：這種指令會誘發它用 Bash 繞過工具鎖直接改檔），修復一律回主 session 路由

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

### 7. Transparency on Tool Usage (Stan wants to SEE the whole process, inline)

Stan explicitly wants long, detailed replies for substantive work, with a running trace of what happened at each step. Not a single banner at the top — a play-by-play.

- **Mark at the point of use, not just the top.** The moment you load a skill / dispatch a subagent / reach for a notable tool, say so right there in the flow, then continue.
  - `⚙️` = a real **Skill** load (via the Skill tool): `humanizer`, `impeccable`, `superpowers:brainstorming`, etc.
  - `🤖` = a **subagent / Agent / Workflow agent** dispatch (name it).
  - plain tools (`Read`/`Edit`/`Bash`/`Grep`/`Workflow`) — name them in the trace too; they are NOT skills, don't badge them with ⚙️.
- **End every multi-step reply with a one-line footer / 對帳單:** `📋 本回合：skill=… ｜ 工具=… ｜ 子代理=…`. This is the receipt Stan cross-checks.
- **NEVER fake it (謊報 guard).** A `⚙️` marker must correspond to an actual Skill-tool invocation — the `Stop` hook logs real skill loads to `~/.claude/skill-usage/session-*.json`, so a padded marker will not match the record. Don't sprinkle markers to look busy. If a turn used zero skills, the footer says `skill=（無，本回合只用工具）` — that is the honest answer, not a failure.
- **Scope by size.** Substantive / multi-step tasks get the full trace + footer. Trivial one-shot answers stay short — no ceremony, maybe just the footer if any skill fired.
- The keyword-nudge hook (`skill-suggest.py`, UserPromptSubmit) only whispers to me; it never reaches Stan's screen. Anything he should see, I write out myself per the rules above. See memory [[howto-skill-triggering-system]] and [[feedback-inline-skill-trace]].

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

## Output Humanization (繳交 / 對外用語言)

Any text headed for **submission** (reports, assignments, homework) or **external/public use** (emails, posts, public docs, i.e. anything leaving our private working chat) MUST pass through the `humanizer` skill before it is final. Do it proactively; do not wait to be asked. Internal scratch and working text is exempt.

- **Run it (pick by the output's language):** English text -> `/humanizer`; Traditional Chinese text -> `/humanizer-zh-tw`. Both skills live under `~/.claude/skills/`. They strip the AI tells: em/en dashes (hard remove), rule-of-three, AI vocabulary (testament/landscape/delve, 象徵/彰顯/值得一提), excessive boldface, hedging, "not just X, it's Y" / 「不只是X，而是Y」, emojis, curly quotes, canned upbeat conclusions.
- **Self-check:** if the final text still contains an em dash or en dash, it is not done.
- **Then layer Stan's own prefs:** code drops `# ===` divider lines, simplifies docstrings, uses shorter names and fewer comments; reports avoid bold-led paragraphs, do not force exactly-3 lists, use first person, and vary paragraph length.
- Applies to code comments and docstrings in submitted work too, not only prose.
- **Custom rule (Stan):** also cut parenthetical over-explanation, above all glossing a proper noun with its English or full name in parentheses, e.g. 「水晶逃脫（Sky Crystal Escape）」. Fold the aside into the sentence or drop it. Mirrored into both `SKILL.md` files; keep it if a `git pull` ever overwrites them.
