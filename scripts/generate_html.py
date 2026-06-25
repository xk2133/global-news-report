#!/usr/bin/env python3
"""
generate_html.py — Generate Global News Report HTML from structured JSON.

Usage:
    python scripts/generate_html.py \
        --date 20260625 \
        --market-date "Jun 24, 2026" \
        --market-json /tmp/market_data.json \
        --news-json /tmp/news_data.json \
        --template assets/report-template.html \
        --output "Global News Report-20260625.html"
"""
import json
import argparse
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# Sparkline SVG generator
# ---------------------------------------------------------------------------
def make_sparkline(values, ytd_val, prefix):
    """
    Generate inline SVG sparkline.
    values: list of float (closing prices / levels)
    ytd_val: float (YTD % change, determines color)
    prefix: str (unique ID for gradient)
    """
    if not values or len(values) < 2:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1.0
    n = len(values)
    color = "#d32f2f" if ytd_val > 0 else "#2e7d32"

    def to_pt(i, v):
        x = (i / (n - 1)) * 120
        y = 30 - ((v - mn) / rng) * 28
        return f"{x:.1f},{y:.1f}"

    line_pts = " ".join(to_pt(i, v) for i, v in enumerate(values))

    # Area polygon: data points → bottom-right → bottom-left → close
    area_pts = " ".join(f"{to_pt(i, v)}" for i, v in enumerate(values))
    area_pts += f" 120,30 0,30"

    gid = f"g{prefix}"
    svg = (
        f'<svg viewBox="0 0 120 32" width="120" height="32">'
        f'<defs>'
        f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.25"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<polygon fill="url(#{gid})" points="0,30 {area_pts}"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="1.5"'
        f' stroke-linejoin="round" stroke-linecap="round" points="{line_pts}"/>'
        f'</svg>'
    )
    return svg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def chg_class(val):
    """Return CSS class for up/down/not-changed."""
    if val > 0:
        return "up"
    elif val < 0:
        return "down"
    return ""


def pct_str(val):
    """Format percentage with + sign for positive."""
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"


def day_str_macro(val):
    """Format day change for macro indicators."""
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}"


def day_str_us10y(val):
    """Format day change for US 10Y (in bp)."""
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.1f}bp"


# ---------------------------------------------------------------------------
# Build market table rows
# ---------------------------------------------------------------------------
def build_finance_rows(data):
    """
    Build 8 HTML table rows for the Finance section.
    Order: Dow, S&P 500, Nasdaq, US 10Y, DXY, USD/CNH, Gold, WTI
    """
    rows = []

    # --- Indices (3 rows) ---
    for idx in data["indices"]:
        sp = make_sparkline(idx["sparkline"], idx["ytd_pct"], idx["symbol"].lower())
        rows.append(
            f'<tr>\n'
            f'  <td class="name">{idx["name"]}</td>\n'
            f'  <td class="num">{idx["close"]:,.2f}</td>\n'
            f'  <td class="num {chg_class(idx["day_chg_pct"])}">{pct_str(idx["day_chg_pct"])}</td>\n'
            f'  <td class="num {chg_class(idx["ytd_pct"])}">{pct_str(idx["ytd_pct"])}</td>\n'
            f'  <td class="sparkline-cell">{sp}</td>\n'
            f'</tr>'
        )

    # --- Macro (5 rows) ---
    for m in data["macro"]:
        sp = make_sparkline(m["sparkline"], m["ytd"], m["name"].lower().replace(" ", "").replace("10Y", "us10y"))
        display_name = {
            "US10Y": "US 10Y",
            "DXY": "DXY",
            "USDCNH": "USD/CNH",
            "Gold": "Gold",
            "WTI": "WTI",
        }.get(m["name"], m["name"])

        if m["name"] == "US10Y":
            day_str = day_str_us10y(m["day_chg"])
            ytd_str = day_str_us10y(m["ytd"])
            close_str = f'{m["close"]:.2f}%'
        elif m["name"] in ("DXY", "USDCNH"):
            day_str = day_str_macro(m["day_chg"])
            ytd_str = f'{m["ytd"]:+.2f}%'
            close_str = f'{m["close"]:,.4f}'
        else:
            day_str = day_str_macro(m["day_chg"])
            ytd_str = f'{m["ytd"]:+.2f}%'
            close_str = f'{m["close"]:,.2f}'

        rows.append(
            f'<tr>\n'
            f'  <td class="name">{display_name}</td>\n'
            f'  <td class="num">{close_str}</td>\n'
            f'  <td class="num {chg_class(m["day_chg"])}">{day_str}</td>\n'
            f'  <td class="num {chg_class(m["ytd"])}">{ytd_str}</td>\n'
            f'  <td class="sparkline-cell">{sp}</td>\n'
            f'</tr>'
        )

    return "\n".join(rows)


def build_tech_rows(data):
    """
    Build 7 HTML table rows for the Technology section (Mag 7).
    """
    rows = []
    for stock in data["mag7"]:
        sp = make_sparkline(stock["sparkline"], stock["ytd_pct"], stock["symbol"].lower())
        rows.append(
            f'<tr>\n'
            f'  <td class="name">{stock["name"]}</td>\n'
            f'  <td class="num">{stock["close"]:,.2f}</td>\n'
            f'  <td class="num {chg_class(stock["day_chg_pct"])}">{pct_str(stock["day_chg_pct"])}</td>\n'
            f'  <td class="num {chg_class(stock["ytd_pct"])}">{pct_str(stock["ytd_pct"])}</td>\n'
            f'  <td class="sparkline-cell">{sp}</td>\n'
            f'</tr>'
        )
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Build news cards
# ---------------------------------------------------------------------------
def build_news_cards(news_list):
    """
    Build HTML for a list of news cards.
    news_list: list of dict with keys:
      - tag, en_headline, en_summary, cn_headline, cn_summary, source_url, source_name
    """
    cards = []
    for item in news_list:
        tag = item.get("tag", "")
        en_headline = item.get("en_headline", "")
        en_summary = item.get("en_summary", "")
        cn_headline = item.get("cn_headline", "")
        cn_summary = item.get("cn_summary", "")
        source_url = item.get("source_url", "")
        source_name = item.get("source_name", "")

        card = (
            f'<div class="card">\n'
            f'  <div class="tag">{tag}</div>\n'
            f'  <h3>{en_headline}</h3>\n'
            f'  <p>{en_summary}</p>\n'
            f'  <div class="cn-trans">\n'
            f'    <strong>{cn_headline}</strong><br>{cn_summary}\n'
            f'  </div>\n'
            f'  <div class="source">Source: <a href="{source_url}" target="_blank">{source_name}</a></div>\n'
            f'</div>'
        )
        cards.append(card)
    return "\n".join(cards)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate Global News Report HTML")
    parser.add_argument("--date", required=True, help="Report date YYYYMMDD")
    parser.add_argument("--market-date", required=True, help='Market data date e.g. "Jun 24, 2026"')
    parser.add_argument("--market-json", required=True, help="Path to market_data.json")
    parser.add_argument("--news-json", required=True, help="Path to news_data.json")
    parser.add_argument("--template", required=True, help="Path to report-template.html")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    args = parser.parse_args()

    # --- Parse date ---
    dt = datetime.strptime(args.date, "%Y%m%d")
    date_str = dt.strftime("%Y-%m-%d")
    day_of_week = dt.strftime("%A").upper()
    month_str = dt.strftime("%B").upper()
    dd = dt.strftime("%d").lstrip("0")
    yyyy = dt.strftime("%Y")
    time_str = dt.strftime("%H:%M")
    date_full = dt.strftime("%B %d, %Y").replace(" 0", " ")

    # --- Load JSON ---
    with open(args.market_json, "r", encoding="utf-8") as f:
        market_data = json.load(f)

    with open(args.news_json, "r", encoding="utf-8") as f:
        news_data = json.load(f)

    # --- Build market table rows ---
    finance_rows = build_finance_rows(market_data)
    tech_rows = build_tech_rows(market_data)

    # --- Build news cards ---
    finance_cards = build_news_cards(news_data.get("financial", []))
    tech_cards = build_news_cards(news_data.get("technology", []))
    politics_cards = build_news_cards(news_data.get("politics", []))
    other_cards = build_news_cards(news_data.get("other", []))

    # --- Read template ---
    with open(args.template, "r", encoding="utf-8") as f:
        template = f.read()

    # --- Replace placeholders ---
    replacements = {
        "{DATE}": date_str,
        "{DAYOFWEEK}": day_of_week,
        "{MONTH}": month_str,
        "{DD}": dd,
        "{YYYY}": yyyy,
        "{TIME}": time_str,
        "{DATE_FULL}": date_full,
        "{MARKET_DATE}": args.market_date,
        "{FINANCE_ROWS}": finance_rows,
        "{TECH_ROWS}": tech_rows,
        "{FINANCE_CARDS}": finance_cards,
        "{TECH_CARDS}": tech_cards,
        "{POLITICS_CARDS}": politics_cards,
        "{OTHER_CARDS}": other_cards,
    }

    for k, v in replacements.items():
        template = template.replace(k, v)

    # --- Write output ---
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"✅ HTML report generated: {args.output}")
    print(f"   Size: {os.path.getsize(args.output)} bytes")


if __name__ == "__main__":
    main()
