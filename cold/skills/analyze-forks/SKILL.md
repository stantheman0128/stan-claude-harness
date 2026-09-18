---
name: analyze-forks
description: "Analyze a GitHub repository's fork ecosystem and PR patterns to discover what the community is building. Use this skill whenever the user asks about forks, derivative projects, repo ecosystem, community activity, PR patterns, or says things like 'analyze this repo', 'what are people building with X', 'show me interesting forks', 'who forked this', 'what PRs are active', or provides a GitHub repo URL wanting community insights. Also trigger when the user wants to explore how a tool/library is being used or extended by others."
---

# Analyze Forks — GitHub Ecosystem Deep Dive

Analyze a GitHub repo's fork ecosystem and PR activity. The goal is not just listing forks and PRs, but explaining WHY each one is interesting and WHAT it reveals about the community.

## How to use

### Step 1: Run the analysis script

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/analyze_forks.py" owner/repo
```

Options:
- `--max-fork-age DAYS` — Only include forks active within N days (default: 730)
- `--top-forks N` — Deep-dive top N forks for commits/topics (default: 30)
- `--top-prs N` — Deep-dive top N PRs for body/files (default: 20)

For repos with thousands of forks, expect 1-3 minutes. Let the user know.

### Step 2: Understand the output

The JSON has two tiers of data:

**Deep-dived items** (top forks/PRs) have rich data:
- Forks: `recent_commits` (last 10 commit messages + authors) and `topics`
- PRs: `body` (description text), `files` (what files changed), `additions`/`deletions`

**Light items** (remaining forks/PRs) have metadata only:
- Forks: name, description, stars, pushed_at
- PRs: title, comments count, labels, state

### Step 3: Analyze and present

Present in Traditional Chinese. The analysis has two modes depending on data depth.

---

## For deep-dived forks: individual analysis

For each fork that has `recent_commits`, write a focused paragraph explaining:

1. **What they built** — Read the commit messages. What's the actual work? Not "they forked it" but "they rewrote the training loop to support AMD ROCm, added HIP kernels, and benchmarked on MI300X".
2. **Why it matters** — What gap does this fill? Who benefits? Is this solving a problem the original repo ignores?
3. **How active** — Are commits recent? Is it one person or a team? One burst or sustained work?
4. **Verdict** — Is this a serious derivative project, a quick hack, or an experiment? Be honest.

Example of GOOD analysis:
> **miolini/autoresearch-macos** (1,713 stars) — 把 autoresearch 完整移植到 macOS，支援 Apple Silicon 的 Metal Performance Shaders。最近的 commits 顯示他們在優化 MPS backend 的 memory allocation，還加了 ANE (Apple Neural Engine) 的實驗性支援。這是目前生態系裡最成功的衍生專案，解決了原版只支援 NVIDIA CUDA 的最大痛點。活躍度極高，幾乎每天都有 commit。

Example of BAD analysis:
> **miolini/autoresearch-macos** (1,713 stars) — macOS 版本的 autoresearch，有很多星星。

The difference: good analysis reads the commits and explains the SUBSTANCE.

---

## For deep-dived PRs: individual analysis

For each PR that has `body` and `files`, explain:

1. **The problem** — What issue is this PR addressing? Read the body for motivation.
2. **The approach** — What files were changed? What's the technical strategy? (e.g., "adds a new `train_mlx.py` that mirrors `train.py` but uses MLX primitives instead of PyTorch")
3. **Community reception** — How many comments? Was it merged, rejected, or still open? If open for a long time with many comments, that often means it's controversial or complex.
4. **What it reveals** — What does this PR tell us about the project's direction or community needs?

---

## For light items (no deep-dive data): pattern analysis

Group the remaining forks/PRs by theme and explain the PATTERN, not each individual one.

Good pattern analysis:
> **硬體移植浪潮 (43 forks):** 從 macOS 到 Jetson Thor、從 AMD ROCm 到 Tenstorrent，社群幾乎把 autoresearch 搬到了所有能跑 AI 的硬體上。這反映了一個清楚的訊號：原版只支援 NVIDIA GPU 是社群最大的痛點。值得注意的是 Apple Silicon 相關的 fork（~10 個）遠多於 AMD（~3 個），說明 Mac 用戶的需求更迫切。

---

## Final synthesis

After analyzing individual items and patterns, connect the dots:

1. **Fork ↔ PR 的交叉比對** — 如果很多 fork 在做 X，而 PR 也在要求 X，那 X 就是社群最大的未滿足需求
2. **生態系的健康度** — 改名 fork 佔比高代表「衍生型生態」（人們拿去做新東西），低則代表「貢獻型生態」（人們 fork 來提 PR 就走了）
3. **驚喜發現** — 有沒有預期之外的用法？有人把它用在完全不同的領域嗎？
4. **對原 repo 的建議** — 根據 fork 和 PR 的模式，原 repo 應該優先做什麼？

## Tips

- Always provide clickable links so the user can explore further.
- Be honest about forks that look promising but are actually shallow (forked, renamed, maybe one commit, then abandoned).
- Commit messages are your best signal — a fork with 10 meaningful commits is more interesting than one with 100 stars but no original work.
- If a fork's description is identical to the original, look at commits to determine what actually changed.
