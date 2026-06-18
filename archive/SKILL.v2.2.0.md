---
name: global-news-report
description: >
  Generate a professional "Global Top News" HTML report covering Financial, Technology, Political, and Other Highlights.
  Triggers: "Global News Report", "top news", "daily news", "news report", "新闻报告".
  Designed for daily automation (08:30 CST) but can be triggered manually.
version: 2.2.0
agent_created: true
---

# Global News Report Skill (v2.2)

Generate a polished, self-contained HTML report with market data tables and bilingual news cards.

## Output

- **File**: `Global News Report-YYYYMMDD.html` in workspace root
- **Title**: "Global Top News"
- **Display language**: English; cards bilingual (EN + 中文)
- **Color**: Up=Red `#d32f2f`, Down=Green `#2e7d32`

---

## Step 1: Market Data — Wind MCP Only

**CLI** from `C:\Users\kongxy12\.agents\skills\wind-mcp-skill\`:
```
node scripts/cli.mjs call {server} {tool} '{JSON params}'
```
⚠️ Must use `spawnSync` in Node.js scripts (NOT `execSync`) to avoid Windows shell quote escaping.

### 1A: Indices + FX — `get_index_quote` (index_data)

Always available (24/7). Returns minute K-lines; extract last bar for daily close.

| # | Indicator | windcode | Extract from rows[] |
|---|-----------|----------|---------------------|
| 1 | Dow Jones | `DJI.GI` | `rows[-1][0]`=Close, `rows[-1][5]`=Date (`yyyyMMdd`) |
| 2 | S&P 500 | `SPX.GI` | same |
| 3 | Nasdaq | `IXIC.GI` | same |
| 4 | USD/CNY | `USDCNY.IB` | same |

> Note: quote returns MATCH (close), AVGPRICE, VOLUME, TURNOVER, TIME, _DATE columns.
> Day change % requires Open from `rows[0][0]`: `(Close - Open) / Open * 100`.

### 1B: Mag 7 Stocks — `get_global_stock_price_indicators` (global_stock_data)

Always available. Returns PrevClose → exact daily change %.

| # | Stock | windcode |
|---|-------|----------|
| 5 | Apple | `AAPL.O` |
| 6 | Microsoft | `MSFT.O` |
| 7 | Nvidia | `NVDA.O` |
| 8 | Amazon | `AMZN.O` |
| 9 | Meta | `META.O` |
|10 | Alphabet | `GOOGL.O` |
|11 | Tesla | `TSLA.O` |

Parse: `data.rows[0]` contains price, prevClose, change%, volume etc.

### 1C: Macro/Commodity (Gold, WTI, DXY, US 10Y) — `get_economic_data` (economic_data)

**Single call covers all 4 indicators** — `economic_data` endpoint has broader coverage than `index_data` and is available 24/7 (EDB economic database).

```
node scripts/cli.mjs call economic_data get_economic_data \
  '{"metricIdsStr":"美元指数,伦敦现货黄金价格,NYMEX原油期货价格,美国国债收益率10年","freq":"日","beginDate":"20260101","endDate":"{TODAY}"}'
```

**Response structure**: `content[0].text` → parse inner JSON → `data.date[]` + `data.indicatorInfo[]`.
Each indicator has `code`, `name`, `data[]` (same length as `date[]`, null = non-trading day).

**Target codes to filter** (ignore other indicators in the response):

| # | Indicator | Code | Name (中文) | Unit |
|---|-----------|------|-------------|------|
|12 | Gold | `S0031645` | 现货价(伦敦市场):黄金:美元 | USD/oz |
|13 | WTI Crude | `S0180938` | 期货结算价(活跃合约):NYMEX轻质原油 | USD/bbl |
|14 | DXY | `M0000271` | 美元指数 | index pts |
|15 | US 10Y | `G0000891` | 美国:国债收益率:10年 | % |

**Parsing**:
- `date[]` is **forward-chronological** (oldest first, newest last)
- Filter `indicatorInfo` for the 4 codes above, match by `code` field
- Strip nulls for trading-day-only series: `[(date[i], val) for i,val in enumerate(data) if val is not None]`
- Latest value = last non-null entry; YTD history = full array

**Don't use `count`** param — `economic_data` doesn't support it. Always pass `beginDate` + `endDate` (format: `yyyyMMdd`, no dashes).

### 1D: YTD History / Sparkline Data

| Source | Indicators Covered | Date Range | Notes |
|--------|-------------------|------------|-------|
| `get_index_kline` (index_data) | DJI, SPX, IXIC | Jan 1 → today | **Full YTD**, begin_date=`20260101` |
| `get_economic_data` (economic_data) | Gold, WTI, DXY, US 10Y | Jan 1 → today | **Full YTD**, single call with 4 codes |

- **3 indices** → kline YTD range → complete data
- **4 macro** → same `economic_data` call as Step 1C, already covers full YTD
- **Mag 7 YTD**: calculate from year-start price fetched via `get_global_stock_price_indicators` + prevClose comparison against Jan 2

### 1E: Fallback — WebFetch (P1)

Only when Wind MCP returns AUTH_ERROR or NETWORK_ERROR. Fetch individual MarketWatch pages:

| Indicator | URL suffix |
|-----------|-----------|
| DJIA | `marketwatch.com/investing/index/djia` |
| S&P 500 | `marketwatch.com/investing/index/spx` |
| Nasdaq | `marketwatch.com/investing/index/comp` |
| Gold | `marketwatch.com/investing/future/gold` |
| WTI | `marketwatch.com/investing/future/cl.1` |
| DXY | `marketwatch.com/investing/index/dxy` |
| US 10Y | `marketwatch.com/investing/bond/tmubmusd10y` |
| USD/CNY | `marketwatch.com/investing/currency/usdcny` |
| AAPL/MSFT/NVDA/etc | `marketwatch.com/investing/stock/{ticker}` |

**DO NOT use yfinance, Python scripts, Finnhub API, NewsAPI, or TradingEconomics.** Report data = last US trading day close. Wind EDB daily close is authoritative. Real-time sources (TradingEconomics etc.) reflect intraday prices for a different as-of date — never use them as primary source.

---

## Step 2: Collect News (WebSearch max 2 calls)

### Call 1 — All 4 sections merged (`topic: "news"`)

Replace `{DATE}` with today's date:

| Group | Query |
|-------|-------|
| Financial | `"top financial markets stock economy news today {DATE}"` |
| Technology | `"top technology AI chips funding IPO news today {DATE}"` |
| Political | `"top political geopolitics trade diplomacy news today {DATE}"` |
| Other | `"world sports crypto defense highlights news today {DATE}"` |

Aim for 3-5 stories per section.

### Call 2 — Gap Fill (only if section < 2 stories)

Targeted search for the deficient section.

### WebFetch Follow-ups (max 2-3 calls)

Fetch full text for **1 lead story per section** only. Others use search snippets.

### News Filtering Rules

**Source tiers**:
| Tier | Sources | Rule |
|------|---------|------|
| T1 ⭐⭐⭐⭐ | Reuters, AP, Bloomberg, BBC | ≥2 sections must have T1 |
| T2 ⭐⭐⭐ | CNBC, WSJ, FT, MarketWatch, Barron's | Preferred |
| T3 ⭐⭐ | TechCrunch, Wired, The Verge, Ars Technica | Tech section OK |
| T4 ⭐ | Seeking Alpha, Fortune, Forbes | Max 1/report |
| ❌ BANNED | Aggregators/blogs (CoinStats, TechStartups, etc.) | Zero tolerance |

- All sources English-only (NO sina, qq, 36kr, eastmoney)
- CNN capped at ≤2 stories
- Same event → merge into primary section, cite highest-tier source
- Recency hard limit: < 24 hours
- Each section designates 1 lead story (record-breaking, billion$, war, election, etc.)

---

## Step 3: Generate HTML

### Template Reuse

1. Read yesterday's report if exists
2. Patch only: date line, market values, sparklines, news cards
3. Keep unchanged: CSS, tab structure, page layout

### Page Structure

```
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>Global Top News — {Date}</title>
<style>/* copy from prior report */</style></head><body>
<div class="container">
  <div class="header">
    <div class="date">{DayOfWeek, Month DD, YYYY}</div>
    <h1>Global Top News</h1>
  </div>
  <nav class="tab-bar">...</nav>

  <!-- Panel FINANCE: 8-indicator table + 3-5 news cards -->
  <!-- Panel TECH: Mag7 table (7 stocks) + 3-5 news cards -->
  <!-- Panel POLITICS: 2-3 cards -->
  <!-- Panel OTHER: 2-4 cards -->

  <div class="footer">Auto-generated by KK · As of {time} CST</div>
</div>
</body></html>
```

### Market Table Format (Finance panel)

8 rows: Dow, S&P 500, Nasdaq, Gold, WTI, DXY, USD/CNY, US 10Y.
Each row: Name | Price | Day Change (%) | YTD Change (%) | Sparkline SVG (120×32).

### Market Table Format (Tech panel)

7 rows: AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA. Same columns.

### Sparkline SVG

```svg
<svg viewBox="0 0 120 32" width="120" height="32">
  <defs><linearGradient id="g{Id}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{color}" stop-opacity="0.25"/>
    <stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>
  </linearGradient></defs>
  <polygon fill="url(#g{Id})" points="0,30 {areaPts} 120,30"/>
  <polyline fill="none" stroke="{color}" stroke-width="1.5"
    stroke-linejoin="round" stroke-linecap="round" points="{linePts}"/>
</svg>
```
- Color: Red (#d32f2f) if YTD > 0, Green (#2e7d32) if YTD < 0
- Gradient ID unique per row (gDow, gSp, gAapl, etc.)
- Points: x=0..120, y mapped to min/max range within 0..30

### News Card (bilingual)

```html
<div class="card {section}">
  <div class="card-tag">{TAG}</div>
  <div class="card-title">{English Headline}</div>
  <div class="card-desc">{Summary 2-4 sentences with numbers}</div>
  <div class="cn-trans"><strong>{中文标题}</strong><br>{中文摘要}</div>
  <div class="source">Source: <a href="{URL}" target="_blank">{Name}</a></div>
</div>
```

### Event Timeline

Read `.workbuddy/timeline/timelines.json` before generation. If topic has ≥2 entries, insert `<details>` timeline block inside matching card. Update file after generation (append today, clean >30 days).

---

## Quality Checklist

- [ ] All 15 indicators via Wind MCP: 1A quote (4), 1B global_stock (7), 1C economic_data (4)
- [ ] economic_data response parsed: filter by codes (M0000271/S0031645/S0180938/G0000891), forward-chronological
- [ ] Source tiers enforced: T1 ≥2 sections, CNN ≤2, no banned sources
- [ ] De-dup applied; all stories < 24h; each section has 1 lead story
- [ ] Template reused from yesterday (CSS/layout untouched)
- [ ] Title exactly "Global Top News", file named `Global News Report-YYYYMMDD.html`
- [ ] Sparkline colors match YTD direction; gradient IDs unique
- [ ] All source links clickable; every card has `.cn-trans` block
- [ ] Timeline read before, updated after generation
