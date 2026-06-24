---
name: global-news-report
description: >
  Generate a professional "Global Top News" HTML report covering Financial, Technology, Political, and Other Highlights.
  Triggers: "Global News Report", "top news", "daily news", "news report", "新闻报告".
  Can be triggered manually or via automation.

## Environment Dependencies

- **Required**: `Wind MCP Skill` installed and Wind terminal running (for market data)
- **Optional fallback**: If Wind MCP unavailable, skip Step 1 and generate news-only report (Step 2 + Step 3)
- **Path placeholder**: `{WIND_MCP_SKILL_DIR}` — replace with actual path to `wind-mcp-skill` directory (e.g., `C:\Users\<user>\.claude\skills\wind-mcp-skill` on Windows, or equivalent on Linux/macOS)
version: 2.5.1
agent_created: true
---

# Global News Report Skill (v2.5.1)

Generate a polished, self-contained HTML report with market data tables and bilingual news cards.

## Output

- **File**: `Global News Report-YYYYMMDD.html` in workspace root
- **Title**: "Global Top News"
- **Display language**: English; cards bilingual (EN + 中文)
- **Color**: Up=Red `#d32f2f`, Down=Green `#2e7d32`

---

## Step 1: Market Data — Wind MCP Only

**CLI** from `{WIND_MCP_SKILL_DIR}`:
```
node scripts/cli.mjs call {server} {tool} '{JSON params}'
```
> ⚠️ Must use `spawnSync` in Node.js scripts (NOT `execSync`) to avoid shell quote escaping issues.

### [Windows-specific] Subprocess warnings

These only apply on Windows (PowerShell / Git Bash / CMD):

- **spawnSync vs execSync**: `spawnSync` avoids shell escaping issues on Windows; `execSync` may misquote JSON params.
- **Subprocess empty stdout**: Python `subprocess.run([node, cli.mjs, ...])` returns empty stdout on Windows even with correct cwd. Workaround: redirect CLI output to temp files via Bash (`node cli.mjs ... > /tmp/out.json`), then parse with Python. Direct pipe also works (`node cli.mjs ... | python -c ...`).
- **Bash parallel redirect trap**: In Git Bash on Windows, `cmd & cmd2 &` + `>` redirect combos produce **0-byte files**. Always fetch Wind MCP data **serially** (no `&`). Each call must complete before the next.
- **Windows /tmp vs Python tempdir**: Bash redirects to `/tmp/xxx.json`, but Python's `tempfile.gettempdir()` returns `C:\Users\…\AppData\Local\Temp`. Python parse scripts must use the Windows absolute path, NOT `/tmp`.

### [Linux/macOS] Alternative

On Unix-like systems, `subprocess.run()` with `stdout=PIPE` typically works directly. Use `tempfile.gettempdir()` for cross-platform temp paths without manual `/tmp` references.

### 1A: Indices + FX — `get_index_kline` (index_data)

Get daily K-line from late Dec of prior year through today. Returns matrix with columns below.

| # | Indicator | windcode | begin_date |
|---|-----------|----------|------------|
| 1 | Dow Jones | `DJI.GI` | `{YYYYMMDD}` (late Dec prior year) |
| 2 | S&P 500 | `SPX.GI` | `{YYYYMMDD}` (late Dec prior year) |
| 3 | Nasdaq | `IXIC.GI` | `{YYYYMMDD}` (late Dec prior year) |
| 4 | USD/CNH (Offshore) | `USDCNH.FX` | `{YYYYMMDD}` (late Dec prior year) |

> kline columns = TIME(0), OPEN(1), MATCH/close(2), HIGH(3), LOW(4), TURNOVER(5), VOLUME(6), _DATE(9).
> Day Chg = `(rows[-1][2] - rows[-2][2]) / rows[-2][2] * 100` — (latest close - prev day close) / prev day close.
> YTD = `(rows[-1][2] - yearEndClose) / yearEndClose * 100` — yearEndClose = close on Dec 31 of prior year; if Dec 31 is not a trading day, use the last trading day before it.
> ⚠️ kline must span from late Dec of prior year to today, so both prev-day and year-end close are in the data.
> ⚠️ **USD/CNH 口径**: 使用离岸人民币（Offshore CNH），非在岸人民币（CNY）。windcode = `USDCNH.FX`。

### 1B: Mag 7 Stocks — `get_global_stock_price_indicators` (global_stock_data)

Always available. Returns PrevClose → exact daily change %.

⚠️ **One stock per call** — `windcode` does NOT accept comma-separated values. Call 7 times serially.

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
- Day Chg = `(price - prevClose) / prevClose * 100` — already provided by Wind in `change%` field.
- YTD = `(price - yearEndClose) / yearEndClose * 100` — yearEndClose = close on Dec 31 of prior year from `get_stock_kline`. If Dec 31 is not a trading day, use the **last trading day before Dec 31**.
  - ⚠️ If no row with `_DATE=="{YYYYMMDD}"` (Dec 31) exists, use the **last row before Jan 1 of current year** as the year-end baseline.
- YTD Sparkline = full kline `MATCH` column (Jan 2 of current year → today), also from `get_stock_kline`.

### 1C: Macro/Commodity (Gold, WTI, DXY, US 10Y) — `get_economic_data` (economic_data)

**Single call covers all 4 indicators** — `economic_data` endpoint has broader coverage than `index_data` and is available 24/7 (EDB economic database).

```
node scripts/cli.mjs call economic_data get_economic_data \
  '{"metricIdsStr":"美元指数,伦敦黄金,NYMEX原油期货价格,美国国债收益率10年","freq":"日","beginDate":"{YYYYMM}01","endDate":"{TODAY}"}'
# Example for 2026: beginDate="20251201"
# ⚠️ Gold keyword = "伦敦黄金" NOT "伦敦现货黄金价格" — the latter returns service error
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
- Day Chg = `(values[-1] - values[-2]) / values[-2] * 100` — latest vs immediately preceding non-null value
  - **US 10Y exception**: display as basis points (bp): `(values[-1] - values[-2]) * 100` bp
- YTD = `(values[-1] - yearEndVal) / yearEndVal * 100` — yearEndVal = value on Dec 31 of prior year; if non-trading day, use the last trading day before it
  - **US 10Y exception**: display as basis points (bp): `(values[-1] - yearEndVal) * 100` bp
- ⚠️ `beginDate` must reach back to early Dec of prior year (e.g. `"20251201"`) to capture year-end baseline

**Don't use `count`** param — `economic_data` doesn't support it. Always pass `beginDate` + `endDate` (format: `yyyyMMdd`, no dashes).

### 1D: YTD Calculation — CRITICAL

| Source | Indicators Covered | Date Range | Notes |
|--------|-------------------|------------|-------|
| `get_index_kline` (index_data) | DJI, SPX, IXIC, **USD/CNH** | late Dec prior year → today | **Full YTD**, begin_date late Dec prior year (includes year-end close + sparkline data) |
| `get_economic_data` (economic_data) | Gold, WTI, DXY, US 10Y | early Dec prior year → today | **Full YTD**, beginDate early Dec prior year (includes year-end value) |
| `get_stock_kline` (stock_data) | Mag 7 × 7 calls | late Dec prior year → today | **Full YTD**, begin_date late Dec prior year (covers year-end close + sparkline data) |

- **3 indices + USD/CNH** → single kline call each (late Dec prior year → today), covers both year-end close, prev-day close, and full sparkline
- **4 macro** → same `economic_data` call as Step 1C (early Dec prior year → today), covers year-end value
- **Mag 7**: 7 × `get_stock_kline` (late Dec prior year → today) covers year-end close + prev-day close + full YTD sparkline in one call per stock

#### YTD Validation (DO NOT SKIP)

After computing all 15 YTD values, run these sanity checks before generating HTML:

1. **Gold YTD should be negative in 2026** (gold peaked ~$5,400 in Jan and has declined to ~$4,200-4,400 by mid-year)
2. **DXY YTD should be +1% to +3%** (started ~98.3, currently ~99-101)
3. **WTI YTD should be strongly positive** (started ~$57, currently ~$75-80, rally >30%)
4. **US 10Y YTD should be +20 to +35bp** (started ~4.18%, currently ~4.4-4.5%)
5. If any YTD value contradicts these ranges, **re-check your calculation before proceeding**

### 1E: Unified Calculation Formulas

**Day Change**: `(latest - prev) / prev × 100`
**YTD Change**: `(latest - yearEndClose) / yearEndClose × 100`

| Track | latest | prev | yearEndClose |
|-------|--------|------|--------------|
| **A — Index kline** | `rows[-1][2]` (MATCH/close) | `rows[-2][2]` (prev day close) | row with `_DATE` of Dec 31 prior year (or last trading day before it) |
| **B — Stock price_indicators** | col[0] (最新成交价) | col[1] (前收盘价) | from `get_stock_kline`: row with `_DATE` of Dec 31 prior year (or last trading day before it) |
| **C — Macro economic_data** | last non-null value | second-last non-null | value on date of Dec 31 prior year (or last trading day before it) |

> ⚠️ All kline/macro queries must start from Dec of prior year to capture year-end baseline.
> **US 10Y**: Day Chg and YTD displayed as basis points (bp) — `(latest - prev) × 100` and `(latest - yearEndVal) × 100`. Color: yield up = red, yield down = green (same as stock convention).

**Financial Snapshot 展示顺序**（报告表格从左到右，8 列）：

| # | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 指标 | Dow Jones | S&P 500 | Nasdaq | **US 10Y Yield** | **DXY** | **USD/CNH (Offshore)** | Gold | WTI Crude |
| 类别 | 指数 | 指数 | 指数 | **债券** | **汇率** | **汇率** | 商品 | 商品 |

> 分组逻辑：股 → 债 → 汇 → 商。

**口径注释**（表格下方脚注）：

| 指标 | 脚注 |
|------|------|
| USD/CNH (Offshore) | 使用离岸人民币（Offshore CNH），非在岸人民币（CNY） |
| Gold | 伦敦现货黄金，美元/盎司（USD/oz） |
| WTI Crude | NYMEX 原油期货活跃合约结算价，美元/桶（USD/bbl） |

### 1F: Fallback — WebFetch (P1)

Only when Wind MCP returns AUTH_ERROR or NETWORK_ERROR. Fetch individual MarketWatch pages:

| Indicator | URL suffix |
|-----------|-----------|
| DJIA | `marketwatch.com/investing/index/djia` |
| S&P 500 | `marketwatch.com/investing/index/spx` |
| Nasdaq | `marketwatch.com/investing/index/comp` |
| DXY | `marketwatch.com/investing/index/dxy` |
| USD/CNH (Offshore) | `marketwatch.com/investing/currency/usdcnh` |
| Gold | `marketwatch.com/investing/future/gold` |
| WTI | `marketwatch.com/investing/future/cl.1` |
| US 10Y | `marketwatch.com/investing/bond/tmubmusd10y` |
| AAPL/MSFT/NVDA/etc | `marketwatch.com/investing/stock/{ticker}` |

**DO NOT use yfinance, Python scripts, Finnhub API, NewsAPI, or TradingEconomics.** Report data = last US trading day close. Wind EDB daily close is authoritative. Real-time sources (TradingEconomics etc.) reflect intraday prices for a different as-of date — never use them as primary source.

---

## Step 2: Collect News (WebSearch ≤ 6 calls)

### Initial 4 calls — One per section (`topic: "news"`)

Replace `{DATE}` with today's date. Each call targets one section:

| # | Section | Query |
|---|---------|-------|
| 1 | Financial | `"top financial markets stock economy news today {DATE}"` |
| 2 | Technology | `"top technology AI chips funding IPO news today {DATE}"` |
| 3 | Political | `"top political geopolitics trade diplomacy news today {DATE}"` |
| 4 | Other | `"world sports crypto defense highlights news today {DATE}"` |

Aim for 3-5 stories per section.

### Gap-fill ≤ 2 calls (only if section < 2 stories after tier filtering)

Targeted search for the deficient section. Only if the initial call for a section returns < 2 usable stories after applying source-tier filtering.

### WebFetch follow-ups (max 2 calls)

Fetch full text for **1 lead story** only (highest-priority, usually Financial or Political). Others use search snippets.

### News Filtering Rules

**Source tiers**:

| Tier | Sources | Rule |
|------|---------|------|
| T1 | Reuters, AP, Bloomberg, BBC, **WSJ** | 政治板块只能用 T1 |
| T2 | CNBC, **CNN**, NYT, FT, MarketWatch, Barron's, The Information | 金融板块可用 |
| T3 | TechCrunch, Wired, The Verge, Ars Technica, VentureBeat | 仅科技板块可用 |
| BANNED | Aggregators/blogs (CoinStats, TechStartups, CoinTelegraph, ValueWalk, Business Insider tech), Seeking Alpha, Fortune, Forbes | Zero tolerance |

### Section-level source rules

| Section | Allowed tiers | T1 minimum |
|---------|--------------|------------|
| Financial | **T1, T2 only** | ≥ 2 stories must be T1 |
| Technology | **T1, T2, T3** | — |
| Political | **T1 only** | All stories must be T1 |
| Other | T1, T2, T3 | — |

### General rules

- All sources English-only (NO sina, qq, 36kr, eastmoney)
- Same event → merge into primary section, cite highest-tier source
- Recency hard limit: < 24 hours
- Each section designates 1 lead story (record-breaking, billion$, war, election, etc.)

---

## Step 3: Generate HTML

### Built-in Template (self-contained, no dependency on prior report)

Use the following full HTML template. Replace all `{PLACEHOLDERS}` with generated data.

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Global Top News — {DATE}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  * { margin:0; padding:0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Microsoft YaHei', 'PingFang SC', sans-serif;
    background: #f8f9fa; color: #1a1a2e; line-height: 1.6; -webkit-font-smoothing: antialiased;
  }
  .container { max-width: 760px; margin: 0 auto; padding: 32px 20px; }
  .header { text-align: center; margin-bottom: 12px; padding-bottom: 20px; border-bottom: 2px solid #e9ecef; }
  .header .date { font-size: 13px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; color: #868e96; margin-bottom: 8px; }
  .header h1 { font-size: 28px; font-weight: 800; color: #1a1a2e; margin-bottom: 0; }
  .tab-bar { display: flex; gap: 4px; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 28px; padding: 4px; }
  .tab-bar button { flex: 1; text-align: center; padding: 13px 10px; font-size: 12px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; border-radius: 9px; border: none; cursor: pointer; font-family: inherit; white-space: nowrap; background: transparent; color: #868e96; transition: all 0.25s ease; outline: none; -webkit-tap-highlight-color: transparent; }
  .tab-bar button:hover { opacity: 0.85; }
  .tab-bar button .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; vertical-align: middle; margin-top: -2px; }
  .tab-bar button .label { vertical-align: middle; }
  .tab-bar button:not(.active)[data-tab="finance"]:hover { color: #e65100; background: #fff3e0; }
  .tab-bar button:not(.active)[data-tab="tech"]:hover { color: #1565c0; background: #e3f2fd; }
  .tab-bar button:not(.active)[data-tab="politics"]:hover { color: #c62828; background: #fce4ec; }
  .tab-bar button:not(.active)[data-tab="other"]:hover { color: #7b1fa2; background: #f3e5f5; }
  .tab-bar button.active { color: #fff; }
  .tab-bar button.active .dot { background: #fff !important; }
  .tab-bar button.active[data-tab="finance"] { background: #ff9800; }
  .tab-bar button.active[data-tab="tech"] { background: #2196f3; }
  .tab-bar button.active[data-tab="politics"] { background: #e91e63; }
  .tab-bar button.active[data-tab="other"] { background: #9c27b0; }
  button[data-tab="finance"] .dot { background: #ff9800; }
  button[data-tab="tech"] .dot { background: #2196f3; }
  button[data-tab="politics"] .dot { background: #e91e63; }
  button[data-tab="other"] .dot { background: #9c27b0; }
  .panel { display: none; }
  .panel.active { display: block; }
  .section-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; }
  .section-bar.finance { background: #fff3e0; color: #e65100; }
  .section-bar.tech { background: #e3f2fd; color: #1565c0; }
  .section-bar.politics { background: #fce4ec; color: #c62828; }
  .section-bar.other { background: #f3e5f5; color: #7b1fa2; }
  .market-table { width: 100%; border-collapse: collapse; margin-bottom: 16px; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  .market-table th { background: #1a1a2e; color: #fff; font-size: 12px; font-weight: 600; padding: 10px 16px; text-align: left; white-space: nowrap; }
  .market-table td { padding: 9px 16px; font-size: 13px; border-bottom: 1px solid #f1f3f5; }
  .market-table tr:last-child td { border-bottom: none; }
  .market-table td.name { font-weight: 600; color: #1a1a2e; }
  .market-table td.num { font-family: 'Inter', monospace; font-weight: 500; text-align: right; }
  .market-table td.num.up { color: #d32f2f; }
  .market-table td.num.down { color: #2e7d32; }
  .sparkline-cell { width: 130px; text-align: center; }
  .card { background: #fff; border-radius: 12px; padding: 20px 24px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border-left: 4px solid #dee2e6; transition: box-shadow 0.2s, transform 0.2s; }
  .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
  .card.finance { border-left-color: #ff9800; }
  .card.tech { border-left-color: #2196f3; }
  .card.politics { border-left-color: #e91e63; }
  .card.other { border-left-color: #9c27b0; }
  .card .tag { font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #adb5bd; margin-bottom: 6px; }
  .card h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; margin-bottom: 8px; line-height: 1.4; }
  .card p { font-size: 14px; color: #495057; line-height: 1.6; }
  .cn-trans { margin-top: 12px; padding-top: 10px; border-top: 1px dashed #dee2e6; font-size: 13px; color: #6c757d; line-height: 1.7; }
  .cn-trans strong { display: block; font-weight: 600; color: #495057; margin-bottom: 4px; }
  .card .source { display: inline-block; margin-top: 10px; font-size: 11px; color: #adb5bd; font-style: italic; }
  .card .source a { color: #868e96; text-decoration: none; border-bottom: 1px dashed #ced4da; transition: color 0.2s, border-color 0.2s; }
  .card .source a:hover { color: #1a1a2e; border-bottom-color: #1a1a2e; }
  .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e9ecef; font-size: 12px; color: #adb5bd; line-height: 1.8; }
  .footer a { color: #868e96; text-decoration: none; border-bottom: 1px dashed #ced4da; }
  @media (max-width: 640px) {
    .tab-bar { flex-wrap: wrap; }
    .tab-bar button { min-width: calc(50% - 4px); font-size: 11px; padding: 10px 6px; }
    .market-table th, .market-table td { padding: 7px 10px; font-size: 12px; }
    .sparkline-cell { width: 80px !important; }
    .card { padding: 16px; }
    .card h3 { font-size: 15px; }
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="date">{DAYOFWEEK}, {MONTH} {DD}, {YYYY}</div>
    <h1>Global Top News</h1>
  </div>
  <nav class="tab-bar" id="tabBar">
    <button class="active" data-tab="finance" onclick="switchTab('finance')">
      <span class="dot"></span><span class="label">Financial</span>
    </button>
    <button data-tab="tech" onclick="switchTab('tech')">
      <span class="dot"></span><span class="label">Technology</span>
    </button>
    <button data-tab="politics" onclick="switchTab('politics')">
      <span class="dot"></span><span class="label">Political</span>
    </button>
    <button data-tab="other" onclick="switchTab('other')">
      <span class="dot"></span><span class="label">Highlights</span>
    </button>
  </nav>

  <!-- ===== FINANCIAL PANEL ===== -->
  <div class="panel active" id="panel-finance">
    <div class="section-bar finance">Financial Markets</div>
    <table class="market-table">
      <thead><tr><th>Index</th><th>Close</th><th>Day Chg</th><th>YTD</th><th>YTD Trend</th></tr></thead>
      <tbody>{FINANCE_ROWS}</tbody>
    </table>
    <div style="font-size:11px;color:#adb5bd;margin:-8px 0 20px 16px;line-height:1.6;">
      <span>USD/CNH: Offshore CNH (not onshore CNY)</span> &middot; 
      <span>Gold: London spot, USD/oz</span> &middot; 
      <span>WTI: NYMEX active contract, USD/bbl</span>
    </div>
    {FINANCE_CARDS}
  </div>

  <!-- ===== TECHNOLOGY PANEL ===== -->
  <div class="panel" id="panel-tech">
    <div class="section-bar tech">Technology</div>
    <table class="market-table">
      <thead><tr><th>Stock</th><th>Close</th><th>Day Chg</th><th>YTD</th><th>YTD Trend</th></tr></thead>
      <tbody>{TECH_ROWS}</tbody>
    </table>
    {TECH_CARDS}
  </div>

  <!-- ===== POLITICAL PANEL ===== -->
  <div class="panel" id="panel-politics">
    <div class="section-bar politics">Politics &amp; Geopolitics</div>
    {POLITICS_CARDS}
  </div>

  <!-- ===== OTHER HIGHLIGHTS PANEL ===== -->
  <div class="panel" id="panel-other">
    <div class="section-bar other">Other Highlights</div>
    {OTHER_CARDS}
  </div>

  <div class="footer">
    Auto-generated &middot; All sources in English &middot;
    <a href="https://apnews.com" target="_blank">AP News</a> &middot;
    <a href="https://www.cnbc.com" target="_blank">CNBC</a> &middot;
    <a href="https://www.marketwatch.com" target="_blank">MarketWatch</a> &middot;
    <a href="https://www.wsj.com" target="_blank">WSJ</a> &middot;
    <a href="https://www.bloomberg.com" target="_blank">Bloomberg</a> &middot;
    <a href="https://www.reuters.com" target="_blank">Reuters</a><br>
    As of {TIME} CST, {DATE_FULL} &middot; Market data as of {MARKET_DATE} close
  </div>
</div>
<script>
function switchTab(name) {
  document.querySelectorAll('.tab-bar button').forEach(function(b) { b.classList.remove('active'); });
  document.querySelectorAll('.panel').forEach(function(p) { p.classList.remove('active'); });
  document.querySelector('[data-tab="' + name + '"]').classList.add('active');
  var panel = document.getElementById('panel-' + name);
  if (panel) {
    panel.classList.add('active');
    panel.style.opacity = '0';
    panel.style.transition = 'opacity 0.2s ease';
    requestAnimationFrame(function() { panel.style.opacity = '1'; });
  }
}
</script>
</body>
</html>
```

**Tab panel mechanics**: `.panel { display:none } .panel.active { display:block }`. Default active = `#panel-finance`. Switch via `switchTab()` with 0.2s fade-in.

### Market Table Row Template

```html
<tr>
  <td class="name">{NAME}</td>
  <td class="num">{PRICE}</td>
  <td class="num {up|down}">{DAY_CHG}</td>
  <td class="num {up|down}">{YTD_CHG}</td>
  <td class="sparkline-cell">{SPARKLINE_SVG}</td>
</tr>
```

### Sparkline SVG Template

```svg
<svg viewBox="0 0 120 32" width="120" height="32">
  <defs><linearGradient id="g{ID}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{COLOR}" stop-opacity="0.25"/>
    <stop offset="100%" stop-color="{COLOR}" stop-opacity="0.02"/>
  </linearGradient></defs>
  <polygon fill="url(#g{ID})" points="0,30 {AREA_PTS} 120,30"/>
  <polyline fill="none" stroke="{COLOR}" stroke-width="1.5"
    stroke-linejoin="round" stroke-linecap="round" points="{LINE_PTS}"/>
</svg>
```
- Color: Red (`#d32f2f`) if YTD > 0, Green (`#2e7d32`) if YTD < 0
- Gradient ID unique per row (`gDow`, `gSp`, `gAapl`, etc.)
- Points: x=0..120, y mapped to min/max range within 0..30

### News Card Template (bilingual)

```html
<div class="card {SECTION}">
  <div class="tag">{TAG}</div>
  <h3>{ENGLISH_HEADLINE}</h3>
  <p>{ENGLISH_SUMMARY}</p>
  <div class="cn-trans">
    <strong>{CN_HEADLINE}</strong><br>{CN_SUMMARY}
  </div>
  <div class="source">Source: <a href="{URL}" target="_blank">{SOURCE_NAME}</a></div>
</div>
```

- **Source line**: Display only source name(s) and link(s). Do NOT append tier labels (no "· T1/T2", "· T1", etc.). Example: `Source: Reuters · CNBC` — never `Source: Reuters · CNBC · T1/T2`.
- **TAG field**: Short keyword (CHIP REBOUND, WWDC 2026, etc.). Do NOT include tier info in tags.

---

## Quality Checklist

- [ ] All 15 indicators via Wind MCP: 1A quote (4), 1B global_stock (7 × serial calls), 1C economic_data (4)
- [ ] economic_data response parsed: filter by codes (M0000271/S0031645/S0180938/G0000891), forward-chronological
- [ ] YTD sparkline data generated for all 15 indicators
- [ ] **YTD % validated**: Gold YTD ≈ negative in 2026, WTI YTD ≈ strongly positive (+25% to +35%), DXY YTD ≈ +1% to +3%
- [ ] Wind MCP fetches done **serially** (no `&` + `>` parallel redirect; on Windows: use absolute temp paths, not `/tmp`)
- [ ] Independent WebSearch per section (4 calls + ≤2 gap-fill = ≤6 total)
- [ ] Section source rules enforced: Financial (T1≥2 + T1/T2 only), Tech (T1/T2/T3), Politics (T1 only), Other (T1/T2/T3); no banned sources
- [ ] De-dup applied; all stories < 24h; each section has 1 lead story
- [ ] Built-in template used (CSS/layout self-contained, no dependency on prior report)
- [ ] Title exactly "Global Top News", file named `Global News Report-YYYYMMDD.html`
- [ ] All 8 financial indicators + 7 Mag 7 stocks present
- [ ] Sparkline colors match YTD direction; gradient IDs unique
- [ ] All source links clickable; every card has `.cn-trans` block
- [ ] No Chinese news sources used
- [ ] Source line has no tier labels; TAG has no tier info

---

