---
name: yamato-qlist
description: Draft, refine, review, or generate a first version of a VC due-diligence Q list (DD question list / questionnaire) for a startup CDIB Capital is evaluating, in the house style benchmarked on Stan's senior colleague Yamato (a.k.a. Cherith). Use this whenever Stan needs questions to send a target company — whether he says "write a Q list", "幫我寫個初版 Q list", "DD 問題清單", "幫我整理問題給對方", "modify / review my Q list", "write Q list 大和風格", gives a company name / deck / colleague notes and asks what to ask, or asks which angles he is missing. It carries a question bank distilled from past deals (圖靈, Jitera, JTCG, Moldintel) in references/question-bank.md — consult it for concrete, battle-tested phrasings to adapt. Prefer this skill for any q-list work even when Stan doesn't say the exact words "Q list".
---

# CDIB Q List Builder (Yamato-benchmarked)

Use this skill whenever Stan needs to write, upgrade, or scope a Q list for a target company. The list goes to the founder / CEO / IR window, who must formally write back. The goal is **structured, verifiable, hard-to-evade answers that meaningfully advance the investment decision** — not a fishing expedition.

The methodology below is Yamato's (大和 / Cherith), Stan's senior colleague and the internal benchmark. It encodes years of pattern-matching about what gets answered and what gets evaded. `references/question-bank.md` is the concrete companion: ~90 real question patterns from four past deals, organized by dimension and tagged by business model — pull from it and re-anchor to the deal at hand.

## How to use this skill — pick the mode

Stan arrives in one of three modes. Detect which and act:

1. **Review / diff an existing Q list** (he uploads his draft). Diff against his version, mark each row `[原問]` / `[優化]` / `[新增]`, and lead with the *dimensions he is missing*. Apply the "preserve structure, append clauses" rule (technique 4 below) — don't rewrite his questions unless they are fundamentally wrong.
2. **Write a first draft from scratch** (he gives a company name, a deck, a financial report, or a colleague's notes). Follow "Writing a first draft from scratch" below.
3. **Suggest angles** (he asks "what should I ask this company?" / "what am I missing?"). Identify the business model, then surface the highest-leverage angles from the question bank for that model + the dimensions most likely to be the deck's weak point. Keep it to suggestions; don't necessarily produce a full xlsx unless asked.

In every mode, the first analytical step is the same: **identify the business model** (next section), because it determines which extra angles are mandatory.

## Stan's working context

Stan runs the CCBI cross-border (Taiwan–Japan) fund, Pre-A to Series A, US$1–2M tickets. Two standing implications for every Q list:

- **Cross-border is a mandate, not a preference.** Always probe genuine bilateral (TW⇄JP) expansion: revenue by geography, the overseas go-to-market (direct vs local distributor), the first real overseas reference case, and — for parent/subsidiary structures — transfer pricing, inter-entity revenue recognition, and minority protections. A purely domestic play is a weak fit even with strong fundamentals.
- **Ticket size = minority stake.** Governance, side letters, and exit route matter disproportionately because CDIB will not control the company.

## The two-channel rule (most important principle)

**Q lists run on two parallel channels. Use the right channel for the right question.**

- **Channel 1 — Written Q list:** formally sent and formally answered. Must be **restrained and business-focused**. Questions go here when the company can answer with data, documents, or factual statements they'd be comfortable putting on a permanent record (the IR window circulates this list internally).
- **Channel 2 — Verbal management meeting / call:** for questions where **you need to watch the other party's reaction**. Sensitive topics — cap-table anomalies without disclosed consideration, hidden capital commitments, bridge-round price vs Series A target, deck unit-of-measure ambiguities, hidden share transfers, related-party transactions, redemption/liquidation clause rationale, strategic-investor side letters — go here. Writing them down signals adversarial DD, hardens the relationship, and lets the company prepare a clean rehearsed answer.

**Default: when in doubt, the question goes verbal.** Note: some past lists (JTCG, Jitera) *did* put valuation and cap-table items in writing. That's a judgment call driven by relationship maturity and how late-stage the diligence is — flag the tradeoff to Stan rather than applying the rule blindly.

## First-wave constraints

- **Maximum ~20 questions in the first wave.** More than that signals lack of focus and overwhelms the IR window. If you have more, propose splitting: wave 1 (business validation) → wave 2 (governance, cap table, IP, exit) → wave 3 (transaction documents).
- **First wave is business-only:** product, customers, revenue, gross margin, forecast. Governance, share-transfer history, cap-table irregularities, IP litigation → wave 2, or verbal if sensitive.
- **Lawyer / VDD scope (litigation, IP disputes, insurance, regulatory penalties) does not belong in the first wave** — it comes later in the process.
- **New questions must hit the weakest part of the deck narrative**, not random curiosity.

## Recognize the business model first

The right angle-set depends on the model. Match the company to one (or a blend) of these archetypes seen across the deal archive, and pull that archetype's mandatory angles from the question bank:

- **Pure SaaS / subscription** (Jitera-like): seat growth, ARPA evolution, MRR split into New / Expansion / Churn, monthly + annual retention, CAC by channel / payback / CAC:LTV, comps, and **platform-dependency risk** (what if the upstream LLM/platform offers this natively).
- **AI SaaS + reseller/agency hybrid** (JTCG-like): split agency vs own-product revenue *and margin*; **is the base/agency business already profitable on its own**; reseller geographic rights + local same-trade competitors; LLM/API monthly cost + which models; freemium conversion rate; usage-priced (conversation-based) customer counts.
- **Project/services + product hybrid** (圖靈-like): project pricing & how margin is set, outsourcing % of a project; revenue split across SaaS / project / API·VAS; **customer-vs-account definition**; platform infra fee (e.g., on-chain storage); usage-volume trend (certificates / transactions issued per month).
- **Industrial / hardware-embedded AI** (Moldintel-like): install / POC / paid / MRR-contributing **machine counts** as a time series; performance claims (yield, changeover time, energy) with **third-party validation**; software-only vs software+hardware bundle sales; supplier / BOM dependency; strategic-OEM-investor side letters.
- **Blockchain / certificate / token** (圖靈-like): token/infra fee economics, on-chain volume trend, who pays whom on verification, dependency on the underlying chain.

Most CCBI deals are also **cross-border** — layer the cross-border overlay (above) on top of whichever archetype fits.

## Yamato's seven-dimension framework

A Q list that only covers operations and finance is incomplete. Check coverage against all seven:

1. **Operations (營運面)** — customers, deployment, lead time, pipeline, sales motion (direct vs channel).
2. **Product (產品面)** — technology, AI-model data sources, cross-customer training rights, security certs (ISO 27001), data-privacy posture, upstream-platform cost.
3. **Competition (競爭面)** — domestic + international competitors, specific recent competitor moves, differentiation, platform risk, barriers to entry.
4. **Financial (財務面)** — P&L breakdown (by product / channel / geography), gross margin and its composition, opex swings, revenue-quality decomposition, forecast logic, balance-sheet anomalies.
5. **IP (智財權)** — patents (filed / granted, geography, claims), software copyright, employee IP assignment.
6. **Equity structure (股權面)** — cap-table consistency (vs registry, vs SHA), co-founder full-time commitment, strategic-investor side letters, exclusivity / channel binding / purchase guarantees, unusual SHA clause rationale.
7. **Exit (出場)** — M&A vs IPO preference, timing, likely acquirers, target board/market.

Plus **organization & key people**: org chart, headcount by function, hiring plan, key-person CVs **including the CFO** (asking about the CFO signals you're checking IPO readiness).

## Question-design techniques

Apply these when writing or optimizing each question. The first twelve are the core kit; the rest are additional moves recurring in the deal archive.

1. **Time-series, not snapshot.** Replace "累計 X" with "2022 年至今每季 X" to expose the slope and inflection. Cumulative numbers hide *when* things changed.
2. **SaaS unit economics by default.** For any SaaS-positioned company: CAC (by channel), Payback, CAC:LTV, Gross Margin by revenue type — these four together say whether scaling is viable. Plus ARR/MRR trajectory split into (a) one-time license (b) subscription (c) hardware/整機 (d) other.
3. **Number-anchored questions.** Drop the actual % change and absolute figures from the financials into the question itself: "2025 銷售費用年增 148% (NT$5.4M → 13.3M) — 增加項目明細 (人力/行銷/通路/樣機)". Once you've done the math, the company can't brush it off.
4. **Cross-document anomaly detection.** Before drafting, lay cap table, change-of-registration filings (變更登記表 / GCIS), financial statements, deck, and articles of incorporation side by side. Inconsistencies between documents are the highest-quality questions: "Cap table 顯示 X 為 0 股, 但變更登記表仍列 X 為法人董事且持股 Y 股 — 請提供最新核對版 Cap Table 並說明差異". This is also the "preserve structure, append clauses" optimization for existing lists — append a reconciling clause rather than rewriting.
5. **Forward-looking states, not just history.** Append "以及目前合作狀態 (進行中 / 已續約 / 已 churn)" or "以及進度階段". Lagging data is for accountants; leading indicators are for investors.
6. **Sales-funnel framing for pipeline.** Replace "請提供 pipeline" with "weighted pipeline by stage (Qualified / Negotiation / Closed-won), 含逐月新增 ARR 預估與管道轉換率". Companies without sales ops can't answer — that itself is signal.
7. **Definitional questions.** When a deck or statement uses an ambiguous label (商品銷售, 其他收入, Subscription/Advertising/Consulting Revenue), append "此處 X 指的是？". The whole downstream conversation depends on shared definitions.
8. **Specify the period; don't accept "latest".** "2026 年 1-4 月 (or 1-5 月) 自結財務報表", not "最新管理報表".
9. **Strategic-investor risk detection.** When the cap table holds corporate/strategic investors: "與 [strategic investor] 之投資是否伴隨 side letter / 獨家代理 / 通路綁定 / 採購保證 / minimum commitment？" — they usually bind exclusivity that hurts later channel expansion. (Verbal-leaning.)
10. **Co-founder commitment check.** "三位共同創辦人 (XX, XX, XX) 是否仍全職在職？" VCs invest in people; partial commitment kills valuation.
11. **Exit-route question.** Never omit: "潛在退場路徑：M&A vs 上市 之偏好、時程、預計買方、板塊？"
12. **Distribution, not just average.** "平均、最快、最慢 lead time", not "平均 lead time". Distribution reveals risk.

Additional moves from the archive:

13. **Valuation reconstruction.** Back out implied valuation from the cap table and ask them to confirm: "據 Cap Table，目前發行 117,505 股、Pre-A 每股 US$150.1，推得上輪 post-money ≈ US$17.6M，是否另有 ESOP？" Forces a precise valuation conversation. (圖靈)
14. **GM reconciliation + bridge.** When claimed GM ≠ financial-report GM, ask which basis and the main delta: "財報 2025 毛利率 40% 與會議所述 74% 有落差 — 74% 是哪個基礎？主要差異在哪？" And when they forecast a jump: "如何從 38.24% 提升至預期的 62.32%？" (圖靈, JTCG, Moldintel — appears in *every* deal.)
15. **Cost-line-from-zero.** When a cost line was 0 in a prior period and appears now: "[某成本項] 2024 年為 0、2025 出現 — 原因？具體內容？" (JTCG)
16. **Quote the bad number, then ask the cause.** When a document already reveals a weak metric, don't re-request it — quote it and ask why: "Business Plan 顯示 2024→2025 retention 約 55%，流失率偏高原因？" (圖靈)
17. **Base-business profitability.** For hybrids: "在 AI SaaS 產品之前，[代理 / base] 業務是否已實現獲利？" Separates the durable base from the new story. (JTCG)
18. **Platform-dependency risk.** "若 [OpenAI / 上游大廠] 未來自行提供 [類似服務]，公司如何因應並守住定位？" (Jitera)
19. **Unusual-clause rationale.** For any odd SHA/contract term (redemption at 8% compound, CB instead of equity, share transfers to founders), ask the *reason*, not just the fact — and lean verbal. (JTCG)
20. **Reference-customer interview request.** Where appropriate, request a key-customer call as part of DD: "為執行 DD，可否安排 [關鍵客戶] 訪談？" (JTCG; cf. Sony Music for AIPLUX)

## Writing a first draft from scratch

When Stan hands you a company (name, deck, financial report, or colleague notes):

1. **Read what you have.** If a deck or financial report is attached, extract: claimed metrics (ARR/NRR/GM/retention/units), the revenue story, the round (stage, raise, valuation), the cap table, and the named people. Note every number — these become anchors (technique 3).
2. **Classify the business model** (section above) and the cross-border posture.
3. **Run the cross-document pass** (technique 4) if you have ≥2 of {cap table, 變更登記表, financials, deck, SHA}. Flag every inconsistency — these are your best questions.
4. **Pull candidate questions** from `references/question-bank.md` for the matched archetype + all seven dimensions, re-anchoring each placeholder to this deal's actual numbers and names.
5. **Sequence into waves and channels.** First wave ≤20, business-only. Move governance/cap-table/IP/exit to wave 2; move reaction-sensitive items to the verbal channel. Tell Stan explicitly what you routed where and why.
6. **Match the language to the recipient** — English for international/Japanese teams (圖靈, Jitera were in English), Traditional Chinese for domestic teams (JTCG, Moldintel). If unsure, ask Stan.
7. **Mark confidence on inferred items.** If you inferred the business model or a number from a thin deck, say so — Stan flags self-reported metrics as unverified by default.

## Standard structure (output ordering)

```
第一波 (≤20 題, 業務聚焦)
  ├── 文件請求 (3-5: SPA/SHA, multi-year 財簽, 客戶/合作合約樣本, 財測 Excel)
  ├── 營運面 (5-8: Top customers + 合作狀態, lead time 分布, weighted pipeline, SaaS metrics)
  ├── 產品面 (2-3: AI model 資料來源, 跨客戶訓練, ISO 認證, 上游平台成本)
  ├── 競爭面 (1-2: 國內外競品, 具體競爭者動作, platform risk)
  └── 財務面 (4-6: 毛利率拆解與 reconciliation, 收入結構/品質, 費用變動細項, 財測邏輯, 自結期中報)

第二波 (治理 / 股權, after wave-1 response)
  ├── 智財權 (專利地區/範圍, 員工 IP 讓與)
  ├── 股權面 (cap table 對 變更登記表 / 對 SHA, co-founder FTE, 估值重建)
  ├── 出場 (M&A vs IPO 偏好、買方、板塊)
  └── 組織人事 (org chart, headcount by function, key person CV incl. CFO)

(Verbal channel — never written)
  - 無對價揭露的大股東 / 隱藏資本承諾
  - 過橋輪價格 vs Series A 目標價差 ; deck 單位疑問 (USD $150 vs $150K)
  - 退出股東的退出條件 ; 看似關係人的交易
  - 贖回 / CB / 股份轉讓等條款的「當時為何這樣訂」的動機
  - 策略投資人 side letter / 獨家 / 通路綁定
```

## Output format

Produce the Q list as **xlsx** with columns: `No.` / `問題提出日期` / `問題分類` / `問題` / `預期回答格式 / 文件` / `回答 / 回覆`. Optionally add an internal-only `備註` column (tell Stan to hide it before sending). The dated column lets Stan track response latency — itself a diagnostic signal. Add a second sheet for wave strategy, channel legend, and a send-out checklist. (This skill is consulted for q-list *content & structure*; if the deliverable is the actual .xlsx file, also follow the public `xlsx` skill for clean workbook construction.)

If Stan provides an existing list, diff it and mark rows `[原問]` / `[優化]` / `[新增]`.

## What to say to Stan when delivering

Lead with the dimensions his draft was missing (most common gaps: product / IP / competition / exit / strategic-investor side letters / co-founder FTE / balance-sheet anomalies). State what you moved to the verbal channel and why. Confirm the first wave is ≤20; if not, propose the wave split. Keep it terse and high-density — Stan does not want hand-holding. End with the Taiwan-timezone timestamp per his standing preference.
