---
name: global-news-report
description: >
  Generate a professional "Global Top News" HTML report covering Financial, Technology, Political, and Other Highlights.
  Triggers: "Global News Report", "top news", "daily news", "news report", "新闻报告".
  Can be triggered manually or via automation.
version: 3.2.0
agent_created: true
---

# Global News Report Skill (v3.2.0)

Generate a polished, self-contained HTML report with market data tables and bilingual news cards.

## Output

- **File**: `Global News Report-YYYYMMDD.html` in workspace root
- **Title**: "Global Top News" (no subtitle)
- **Language**: English display; news cards bilingual (EN + 中文)
- **Color convention**: Up = Red `#d32f2f`, Down = Green `#2e7d32`

## Architecture

```
SKILL.md                   ← Workflow only (call scripts, don't write HTML)
references/
├── news-filtering.md      ← Source tiers, section rules, BANNED list
└── windows-exec-rules.md  ← Windows-specific execution rules (spawnSync, etc.)
assets/
└── report-template.html   ← HTML/CSS template with {PLACEHOLDERS}
scripts/
├── generate_fetch.py      ← Generates Bash script for Wind MCP data fetching
├── compute_market.py      ← Raw Wind JSON → standardized market_data.json
└── generate_html.py       ← market_data.json + news_data.json → final HTML
```

---

## Step 1: Market Data

### 1a. Pre-flight Probe

```bash
cd {WIND_MCP_SKILL_DIR} && node scripts/cli.mjs call economic_data get_economic_data '{"metricIdsStr":"M0000271","freq":"日","beginDate":"{TODAY-5}","endDate":"{TODAY}"}'
```
→ If `AUTH_ERROR` or `TEMPORARILY_UNAVAILABLE`: **skip to 1d (P1 Fallback)**.

### 1b. Fetch Data

```bash
python scripts/generate_fetch.py --date {YYYYMMDD} --market-date {LAST_TRADING_DAY} --wind-mcp-dir {WIND_MCP_SKILL_DIR}
bash /tmp/fetch_market.sh
```

### 1c. Compute Standardized JSON

```bash
python scripts/compute_market.py --date {YYYYMMDD} --tmpdir /tmp --output /tmp/market_data.json
```

→ Output: `/tmp/market_data.json` (status: `ok` / `partial` / `error`).

### 1d. P1 Fallback (only if 1a probe failed)

WebFetch MarketWatch for each indicator (Dow, S&P, Nasdaq, Gold, WTI, DXY, USD/CNH, US 10Y).

---

## Step 2: News Collection → `references/news-filtering.md`

### What to do

1. **WebSearch** (≤6 calls): 4 sections × 1 call + ≤2 gap-fill calls (gap-fill only if section has <2 stories after tier filtering)
2. **WebFetch** (≤2 calls): Full text for 1 lead story only; others use snippets
3. **Filter**: Apply `references/news-filtering.md` rules (tiers, de-dup, recency)

### Output格式说明

```json
{"financial": [{...}], "technology": [{...}], "politics": [{...}], "other": [{...}]}
```

Each story: `{"tag":"", "en_headline":"", "en_summary":"", "cn_headline":"", "cn_summary":"", "source_url":"", "source_name":""}`

Required: all fields non-empty; `source_url` must be full clickable URL.

---

## Step 3: Generate HTML

**NO manual HTML.** Run `scripts/generate_html.py`:

```bash
python scripts/generate_html.py \
  --market-json /tmp/market_data.json \
  --news-json /tmp/news_data.json \
  --output "Global News Report-{YYYYMMDD}.html"
```

---

## Quality Checklist

- [ ] Step 1a: Wind MCP probe passed (or P1 fallback used)
- [ ] Step 1c: `market_data.json` status = `ok` or `partial`
- [ ] Step 1c: YTD sanity check passed (script prints warnings if not)
- [ ] Step 2: `news_data.json` written, all fields non-empty
- [ ] Step 2: News source rules enforced (`references/news-filtering.md`)
- [ ] Step 3: HTML generated, file size >50KB
- [ ] Output file: `Global News Report-{YYYYMMDD}.html`
