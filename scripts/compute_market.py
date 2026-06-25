#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compute_market.py — Market Data Validator & Calculator (v1.0.0)

Reads Wind MCP raw output files from /tmp, validates, computes metrics,
and outputs standardized JSON for HTML report generation.

Usage:
    python scripts/compute_market.py --date 20260625 --tmpdir C:/Users/.../Temp --output /tmp/market.json

Expected input files in tmpdir:
    Track A:  dji.json, spx.json, ixic.json
    Track B:  aapl_price.json, msft_price.json, ... (7 files)
              aapl_kline.json, msft_kline.json, ... (7 files)
    Track C:  macro.json

EDB codes are HARDCODED — single source of truth. LLM never touches metricIdsStr directly.
"""

import json, os, sys, argparse, glob
from datetime import datetime

# ═══════════════════════════════════════════
# SINGLE SOURCE OF TRUTH — EDB Codes
# ═══════════════════════════════════════════

# Finance table order: 股 → 债 → 汇 → 商
# Indices: Dow, S&P 500, Nasdaq (hardcoded in INDICES)
# Then macro in this order: US10Y, DXY, USDCNH, Gold, WTI
EDB_CODES = {
    "US10Y":  {"code": "G0000891", "name": "美国:国债收益率:10年", "unit": "%", "is_bp": True},
    "DXY":    {"code": "M0000271", "name": "美元指数", "unit": "pts"},
    "USDCNH": {"code": "G0002329", "name": "美元兑人民币", "unit": "CNY/USD"},
    "Gold":   {"code": "S0031645", "name": "现货价(伦敦市场):黄金:美元", "unit": "USD/oz"},
    "WTI":    {"code": "S0180938", "name": "NYMEX轻质原油", "unit": "USD/bbl"},
}

MAG7 = [
    ("AAPL", "Apple"),
    ("MSFT", "Microsoft"),
    ("NVDA", "Nvidia"),
    ("AMZN", "Amazon"),
    ("META", "Meta"),
    ("GOOGL", "Alphabet"),
    ("TSLA", "Tesla"),
]

INDICES = [
    ("DJI", "dji.json", "Dow Jones"),
    ("SPX", "spx.json", "S&P 500"),
    ("IXIC", "ixic.json", "Nasdaq"),
]

YTD_CHECKS = {
    "Gold":   (-100, -0.1,   "Gold YTD should be negative (peaked ~$5,400 Jan, now ~$4,100-4,400)"),
    "DXY":    (0.5, 5.0,     "DXY YTD +1% to +3% (started ~98.3, now ~99-101)"),
    "WTI":    (15, 45,       "WTI YTD strongly positive +25% to +35% (started ~$57, now ~$73-80)"),
    "US10Y":  (10, 50,       "US 10Y YTD +20 to +35bp (started ~4.18%, now ~4.4-4.5%)"),
}


# ═══════════════════
# HELPERS
# ═══════════════════

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    return json.loads(raw)


def unwrap_mcp(raw):
    """Unwrap MCP response: content[0].text → inner JSON"""
    return json.loads(raw["content"][0]["text"])


def parse_kline(inner):
    """Extract (date, close) pairs from kline response."""
    data = inner["data"]
    cols = data["columns"]
    rows = data["rows"]
    cidx = next(i for i, c in enumerate(cols) if c["name"] in ("MATCH", "close", "CLOSE"))
    didx = next(i for i, c in enumerate(cols) if c["name"] == "_DATE")
    vals = [(str(r[didx]), float(r[cidx])) for r in rows if r[cidx] is not None]
    return vals


def parse_price(inner):
    """Extract price data from stock price indicators.
    Mag7 response columns: 最新交易日(0), 交易时间(1), 最新成交价(2), 前收盘价(3), ...
    """
    row = inner["data"]["rows"][0]
    close = float(row[2]) if row[2] else None
    prev = float(row[3]) if len(row) > 3 and row[3] else None
    chg = round((close - prev) / prev * 100, 2) if close and prev else None
    return {"close": close, "prev_close": prev, "change_pct": chg}


def parse_economic_data(inner):
    """Extract indicator data from economic_data response."""
    data = inner["data"]
    dates = data["date"]
    result = {}
    for info in data["indicatorInfo"]:
        code = info["code"]
        vals = [(d, float(v)) for d, v in zip(dates, info["data"]) if v is not None]
        result[code] = {"name": info.get("name", ""), "values": vals}
    return result


def find_year_end(values):
    """Last value in Dec 2025."""
    for d, v in reversed(values):
        if d.startswith("202512"):
            return v
    return values[0][1] if values else 0  # fallback


def compute_metrics(values, year_end, is_bp=False):
    """Day Chg%, YTD%, sparkline from (date, value) series.
    
    is_bp: Day Chg & YTD both in basis points (for yields like US 10Y).
    Default: Day Chg & YTD in % (latest - prev) / prev * 100.
    """
    if len(values) < 2:
        return {"latest": None, "day_chg": None, "ytd": None, "sparkline": []}
    latest = values[-1][1]
    prev = values[-2][1]
    if is_bp:
        day_chg = round((latest - prev) * 100, 2)      # bp
        ytd = round((latest - year_end) * 100, 2)       # bp
    else:
        day_chg = round((latest - prev) / prev * 100, 2) if prev else 0
        ytd = round((latest - year_end) / year_end * 100, 2) if year_end else 0
    return {
        "latest": latest,
        "day_chg": day_chg,
        "ytd": ytd,
        "sparkline": [v for _, v in values],
    }


# ═══════════════════
# MAIN
# ═══════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--tmpdir", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    errors = []
    output = {"status": "ok", "date": args.date, "market_date": "", "preflight": {},
              "indices": [], "macro": [], "mag7": [], "ytd_validation": {"passed": True, "checks": []},
              "errors": errors}

    td = args.tmpdir.replace("\\", "/")
    def fpath(name):
        return os.path.join(td, name) if os.sep in name or "/" in name else os.path.join(td, name)

    # —— TRACK A: Indices ——
    for sym, fname, name in INDICES:
        try:
            inner = unwrap_mcp(load_json(fpath(fname)))
            vals = parse_kline(inner)
            ye = find_year_end(vals)
            m = compute_metrics(vals, ye)
            output["indices"].append({
                "name": name, "symbol": sym,
                "close": m["latest"], "day_chg_pct": m["day_chg"], "ytd_pct": m["ytd"],
                "sparkline": m["sparkline"],
            })
            if not output["market_date"]:
                output["market_date"] = vals[-1][0] if vals else ""
        except Exception as e:
            errors.append(f"Track A {name}: {e}")

    # —— TRACK C: Macro ——
    try:
        inner = unwrap_mcp(load_json(fpath("macro.json")))
        edb = parse_economic_data(inner)

        # VALIDATE codes
        for label, cfg in EDB_CODES.items():
            code = cfg["code"]
            if code not in edb:
                errors.append(f"Track C: {label} ({code}) MISSING from response — re-query by code alone")
                continue
            vals = edb[code]["values"]
            ye = find_year_end(vals)
            is_bp = (label == "US10Y")
            m = compute_metrics(vals, ye, is_bp=is_bp)
            output["macro"].append({
                "name": label, "code": code, "name_cn": cfg["name"], "unit": cfg["unit"],
                "close": m["latest"], "day_chg": m["day_chg"], "ytd": m["ytd"],
                "sparkline": m["sparkline"],
                "latest_date": vals[-1][0] if vals else "",
            })
            if not output["market_date"]:
                output["market_date"] = vals[-1][0] if vals else ""
    except Exception as e:
        errors.append(f"Track C: {e}")

    # —— TRACK B: Mag 7 ——
    for sym, name in MAG7:
        kline_file = fpath(f"{sym.lower()}_kline.json")
        price_file = fpath(f"{sym.lower()}_price.json")
        try:
            # Price
            inner_p = unwrap_mcp(load_json(price_file))
            p = parse_price(inner_p)
            # Kline
            inner_k = unwrap_mcp(load_json(kline_file))
            vals = parse_kline(inner_k)
            ye = find_year_end(vals)
            m = compute_metrics(vals, ye)
            output["mag7"].append({
                "name": name, "symbol": sym,
                "close": p["close"],
                "day_chg_pct": round(p["change_pct"], 2) if p["change_pct"] is not None else None,
                "ytd_pct": m["ytd"],
                "sparkline": m["sparkline"],
            })
        except Exception as e:
            errors.append(f"Track B {name}: {e}")

    # —— YTD Validation ——
    macro_by_name = {m["name"]: m for m in output["macro"]}
    for name, (lo, hi, desc) in YTD_CHECKS.items():
        if name not in macro_by_name:
            output["ytd_validation"]["checks"].append({"name": name, "pass": False, "reason": "data missing"})
            output["ytd_validation"]["passed"] = False
            continue
        actual = macro_by_name[name]["ytd"]
        passed = lo <= actual <= hi
        output["ytd_validation"]["checks"].append({
            "name": f"{name} YTD", "expected_range": f"[{lo}, {hi}]",
            "actual": actual, "pass": passed, "desc": desc,
        })
        if not passed:
            output["ytd_validation"]["passed"] = False

    # —— Status ——
    total = len(output["indices"]) + len(output["macro"]) + len(output["mag7"])
    if total < 10:
        output["status"] = "error"
    elif total < 15 or errors:
        output["status"] = "partial"

    # —— Output ——
    out = args.output
    if out.startswith("/tmp/"):
        out = os.path.join(os.environ.get("TEMP", os.path.dirname(__file__)), os.path.basename(out))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Status: {output['status']} | {total}/15 indicators | errors: {len(errors)}")
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
