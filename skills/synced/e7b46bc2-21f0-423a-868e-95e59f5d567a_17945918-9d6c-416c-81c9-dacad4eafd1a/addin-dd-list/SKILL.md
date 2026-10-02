---
name: addin-dd-list
description: Fill in one row of Addin Ventures' DD tracking sheet, output as a review table plus per-field code blocks for one-click copy into Google Sheets. Use this skill whenever Stan mentions adding a company to the DD list, deal tracker, deal pipeline, investment tracking sheet, or needs to log a new deal. Also trigger on phrases like "DD list 加一筆", "加到追蹤表", "填這間公司到表格", "整理成 DD 表格", or when Stan provides a company (name, URL, deck, or notes from a colleague) in the context of pipeline tracking — even if he doesn't explicitly say "DD list".
---

# Addin DD List Row

Fill one row of Addin Ventures' Deal tracking spreadsheet. Output format is optimized for one-click copy-paste per cell into Google Sheets.

## Column order (18 columns, do not change)

```
Deal | Kickoff Date | Stage | Round | Pre-M | Round Size | Budget | DRI | Aa | Log | Data Room | Categories | Sub Categories | Note | HQ Country | Market | Source | Source2
```

## Workflow

1. **Gather input.** Stan's input is variable — any combination of: company name, website URL, pitch deck, colleague notes (Brandon / Uly / Joyce / a referrer), or just the name. Use whatever is provided as source of truth.

2. **Fill gaps via search only when needed.** If key identifying info (website, product, market, HQ) is missing, use `web_search` and/or `web_fetch`. For JS-rendered sites that don't render (e.g. 1Robot pattern), try search snippets / LinkedIn / Crunchbase, and note it.

3. **Fill each column** using the rules below. Unknown → `N/A`. Stan prefers N/A over guessing on hard numbers (valuation, round size).

4. **Output** in the format specified in "Output format" below.

5. **Below the output**, add 1–3 short bullets flagging: (a) Low-confidence fields, (b) hard-filter misses against Addin's criteria.

## Column rules

### Deal
Company name in the founders' own casing. Keep punctuation (e.g. `namecard.ai`, `myflourish.ai`, `Arklex.AI`, `Qlo (Actuarance)`).

### Kickoff Date
Month Addin started evaluating. Format `YYYY/M` or `YYYY/MM`.
**Default: current month.** Only override if Stan specifies a different start date.

### Stage
- `Pre-PMF` — no live product, pre-launch, pilot without revenue traction, or MVP with unclear retention
- `PMF` — paying customers with measurable retention/growth, clear product-market fit

If genuinely unclear: default `Pre-PMF`, flag Low confidence.

### Round
The round currently being raised (not the last closed).
`Angel` / `Pre-Seed` / `Seed` / `Pre-A` / `Series A` / `Series B`

### Pre-M (Pre-money valuation)
- Known: `$X,XXX,XXX` format (e.g. `$8,500,000`)
- Unknown / not disclosed: `N/A`
- **Addin hard filter**: <$10M (US) or <$2M (TW). Flag if above.

### Round Size
- Known: `$X,XXX,XXX`
- Unknown: `N/A`

### Budget
Addin's intended check size.
**Default: `$100,000`.** Only change if Stan explicitly states otherwise (e.g. Calyx `$2,000,000` for Series B).

### DRI, Aa
Both `N/A`. Stan fills these manually.

### Log, Data Room
Both `N/A`. These are Notion / Drive links Stan adds separately.

### Categories
Free-text industry tag. Existing values (prefer these; create new only if nothing fits):

`Productivity & Utilities` (default for AI agents, generic SaaS) / `Sales Tech` / `Sport Tech` / `Property Tech` / `Media & Entertainment` / `Security` / `Blockchain` / `Edtech` / `Insurance` / `Healthcare` / `人工智慧 (AI)` (fallback)

### Sub Categories
Match the sheet's exact formatting (spaces around dash):
- `B2B - SME` — small / mid businesses
- `B2B - Ent` — enterprises
- `B2C` — direct to consumers
- `B2B2C` — sold through a business to end consumers

### Note
One sentence in Traditional Chinese, terse. Product + customer in one breath. No marketing fluff. Chinese/English mix is fine.

Good: `股市交易資訊 AI Agent` / `布料掃描機，AI 材質辨識` / `AI 視覺辨識重量 for 養雞場 + 屠宰排程`
Bad: `革命性的 AI 平台，賦能企業數位轉型`

### HQ Country
Two-letter ISO 3166-1 alpha-2 code: `TW`, `US`, `JP`, `DE`, `VN`, `CN`, etc.

### Market
Two-letter code(s). Multiple markets use comma or space as seen in sheet: `US`, `TW US`, `US,TW, CN`.

**Addin hard filter:** US-Taiwan corridor required. Flag if missing.

### Source
`Referral` / `GP Network` / `Partner Network` / `N/A`

### Source2
Name of person who introduced: `Brandon`, `Uly`, `Kate`, `Norman`, `Louis`, etc. `N/A` if unknown.

## Output format

For EACH company, output these sections in order:

### Section 1 — Heading
A markdown H2 with the company name: `## {Company Name}`

### Section 2 — Review table
A 2-column markdown table of all 18 fields in column order. Lets Stan scan the row before copying.

```markdown
| Column | Value |
|---|---|
| Deal | {value} |
| Kickoff Date | {value} |
| Stage | {value} |
...
| Source2 | {value} |
```

### Section 3 — Per-field code blocks (one-click copy)

For EACH of the 18 columns in order, output: bolded column name, then a fenced code block on the next line containing only the value. Each code block gives Stan a copy button per field.

Include **every** field, even N/A ones — Stan may want to paste N/A literally.

Format:

    **Deal:**
    ```
    {value}
    ```

    **Kickoff Date:**
    ```
    {value}
    ```

... (continue through all 18 columns)

### Section 4 — Confidence notes
1–3 short bullets flagging:
- **Low-confidence guesses** (Stage, Categories, Sub Categories inferred without strong signal)
- **Hard-filter misses** (Pre-M > $10M, no US-TW corridor, not B2B SaaS / AI-enabled, not Pre-Seed/Seed)
- **Unknowns worth chasing** (e.g. "Pre-M 未披露，下次 call 可確認")

## Batch mode (multiple companies)

When Stan gives multiple companies in one request:
- Output each company as its own `## {Company}` section with table + per-field code blocks, separated by `---` horizontal rules.
- **Do not** combine companies into one table — Stan copies one company at a time.
- Confidence notes go after each company's code blocks (not aggregated at the end).

If the batch is very large (>5 companies), ask Stan first whether he wants the full per-field code block treatment for every company, or just the review tables (faster to produce but no per-cell copy buttons).

## When to ask questions vs. guess

Stan processes multiple deals and prefers fewer interruptions.

- **Guess + flag Low confidence**: Stage, Categories, Sub Categories.
- **Fill N/A**: financial numbers when not stated (Pre-M, Round Size).
- **Ask (1 focused question, no more)** only when ambiguity materially changes hard-filter fit — e.g. can't tell B2B vs B2C at all, or can't locate the company.

## Example

**Input:** "加一筆 Zeabur, AI code-to-deployment service, HQ US, targets US/TW/CN, seed round $1M, referred by Norman, April 2025"

**Output:**

## Zeabur

| Column | Value |
|---|---|
| Deal | Zeabur |
| Kickoff Date | 2025/4 |
| Stage | Pre-PMF |
| Round | Seed |
| Pre-M | N/A |
| Round Size | $1,000,000 |
| Budget | $100,000 |
| DRI | N/A |
| Aa | N/A |
| Log | N/A |
| Data Room | N/A |
| Categories | Productivity & Utilities |
| Sub Categories | B2C |
| Note | AI Code to Deployment Services |
| HQ Country | US |
| Market | US,TW, CN |
| Source | Referral |
| Source2 | Norman |

**Deal:**
```
Zeabur
```

**Kickoff Date:**
```
2025/4
```

**Stage:**
```
Pre-PMF
```

**Round:**
```
Seed
```

**Pre-M:**
```
N/A
```

**Round Size:**
```
$1,000,000
```

**Budget:**
```
$100,000
```

**DRI:**
```
N/A
```

**Aa:**
```
N/A
```

**Log:**
```
N/A
```

**Data Room:**
```
N/A
```

**Categories:**
```
Productivity & Utilities
```

**Sub Categories:**
```
B2C
```

**Note:**
```
AI Code to Deployment Services
```

**HQ Country:**
```
US
```

**Market:**
```
US,TW, CN
```

**Source:**
```
Referral
```

**Source2:**
```
Norman
```

- Stage 推測 Pre-PMF — 無公開 ARR/留存數據 (Low)
- Pre-M 未揭露，需確認 <$10M 門檻

## Reference: Addin's hard filters

- **Stage**: Pre-Seed / Seed (Angel OK)
- **Pre-money**: <$10M US / <$2M TW
- **Sector**: B2B SaaS or AI-enabled deep tech
- **Corridor**: US-Taiwan (strict)

Flag any miss inline in confidence notes. Don't block output — Stan tracks deals even if they don't pass filters.
