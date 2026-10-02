# Effort 曲線與實測

SKILL.md「Effort 速查」與「升階路徑」的佐證。

## 官方曲線

- 舊實測曲線（Opus 5，僅供比例參考）：FrontierBench low 25% → high 39% → xhigh 44.4% → max 43%（不再漲）。
- **Opus 5.5 官方曲線（System Card §8）**：CursorBench medium 52.5% / high 56.0% / max 57.8%，high 每題約 $4 已勝過 Fable 5.1 max 且只花其四分之一（p179）；GDPval-AA xhigh 1820 ≈ max 1846 但 output token 少 51%（p209）；AA-Briefcase xhigh 少 41% token（p210）；Terminal-Bench 4.0 xhigh 66.4 vs max 64.8「在雜訊內」（p178）；**FrontierCode 在 medium 最高（54.6），medium 以上反而下降**，因為高 effort 會改超出範圍的東西被扣分（p176）。結論：coding 給 medium~high，只有明確要更多推理的評測才上 xhigh，max 幾乎沒有理由。
- Sonnet 5.5 的 effort 曲線與成本在 `model-picks.md` 的 Sonnet 5.5 System Card 重點。

## Claude Code 團隊實測

- **Claude Code 團隊實測**（Thariq，claude.dev「Spending your effort」2026-09-25；Terminal-Bench 3.0 內部跑法、每題 5 次、Fable 5.1 關安全防護，數字不能跟排行榜比）：
  - effort 主要改變驗證與邊界測試的量、以及自己下判斷的程度；檔位越高，替你做的假設越多。
  - 高 effort 修的是漏邊界不是方向錯：Fable 5.1 low→max 通過 140→214（共 370 次）、漏邊界類 59→24，但「選錯解讀」25→47 增加。
  - 最吃 effort 的領域（Fable 5.1 低檔→高檔通過率）：Security 64→87%、Hardware 34→75%；規則手冊型工作幾乎不動：Operations 12→22%、Media 18→30%。token 中位數 73k→222k。
  - Opus 5.5 例：儲存引擎 crash 修復 0/5→4/5（xhigh）、線性規劃 solver 0/5→5/5（high）、GSEA 分析 0/5→4/5（high），差別都在有沒有先重現、有沒有拿獨立解法對照測。
- 經驗法則與推薦迴圈在 SKILL.md「Effort 速查」。
