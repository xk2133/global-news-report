#!/usr/bin/env python3
"""
Generate a Bash script with all Wind MCP CLI calls for market data fetching.
Output: /tmp/fetch_market.sh — LLM runs `bash /tmp/fetch_market.sh` via Bash tool.

CRITICAL: All node calls use `cd {CLI_DIR} && node scripts/cli.mjs ...`
because cli.mjs requires its working directory for relative path resolution.
"""
import json, os, sys, argparse, tempfile

CLI_DIR = None  # set from --wind-mcp-dir
TMP = None       # set from --tmpdir or tempfile.gettempdir()

EDB_CODES = "G0000891,M0000271,G0002329,S0031645,S0180938"  # US10Y,DXY,USDCNH,Gold,WTI
INDICES = [("DJI.GI", "dji"), ("SPX.GI", "spx"), ("IXIC.GI", "ixic")]
MAG7 = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA"]


def cli_call(call_num, label, server, tool, params_json, outfile):
    """Generate a bash command line for one Wind MCP CLI call.
    Uses `cd {CLI_DIR} && ...` because cli.mjs requires CWD for relative path resolution.
    Output file goes to `{TMP}/...`."""
    return (
        f'echo "[{call_num}/19] {label}..."\n'
        f'cd {CLI_DIR} && node scripts/cli.mjs call {server} {tool} '
        f"'{params_json}' > \"{TMP}/{outfile}\" 2>&1"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="Target date YYYYMMDD")
    ap.add_argument("--market-date", required=True, help="Last trading day YYYYMMDD")
    ap.add_argument("--wind-mcp-dir", default=None,
                    help="Path to wind-mcp-skill directory (default: auto-detect)")
    ap.add_argument("--tmpdir", default=None,
                    help="Output directory for JSON files (default: system temp)")
    args = ap.parse_args()

    global CLI_DIR, TMP
    # Auto-detect wind-mcp-skill directory
    if args.wind_mcp_dir:
        CLI_DIR = args.wind_mcp_dir.replace("\\", "/")
    else:
        # Try common locations
        candidates = [
            os.path.expanduser("~/.claude/skills/wind-mcp-skill"),
            os.path.expanduser("~/.workbuddy/skills/wind-mcp-skill"),
        ]
        CLI_DIR = next((d for d in candidates if os.path.isdir(d)), None)
        if not CLI_DIR:
            print("ERROR: Cannot find wind-mcp-skill. Use --wind-mcp-dir to specify path.")
            sys.exit(1)
    # Convert to Git Bash path format (/c/Users/...)
    if ":" in CLI_DIR:
        drive, rest = CLI_DIR.split(":", 1)
        CLI_DIR = f"/{drive.lower()}{rest}"

    # Output temp directory
    if args.tmpdir:
        TMP = args.tmpdir.replace("\\", "/")
    else:
        TMP = os.environ.get("TEMP", os.environ.get("TMPDIR", tempfile.gettempdir())).replace("\\", "/")

    lines = [
        "#!/bin/bash",
        "set -e",
        f'echo "=== Fetching market data for {args.date} ==="',
        "",
    ]

    # Pre-flight (1)
    lines.append(cli_call(
        1, "Pre-flight DXY",
        "economic_data", "get_economic_data",
        json.dumps({"metricIdsStr": "M0000271", "freq": "日",
                     "beginDate": "20260620", "endDate": args.date}),
        "preflight.json",
    ))

    # Track C: Macro (1)
    lines.append(cli_call(
        2, "Track C: Macro (5 indicators)",
        "economic_data", "get_economic_data",
        json.dumps({"metricIdsStr": EDB_CODES, "freq": "日",
                     "beginDate": "20251201", "endDate": args.date}),
        "macro.json",
    ))

    # Track A: Indices (3)
    call_num = 3
    for windcode, fname in INDICES:
        lines.append(cli_call(
            call_num, f"Track A: {windcode}",
            "index_data", "get_index_kline",
            json.dumps({"windcode": windcode, "begin_date": "20251201",
                         "end_date": args.date, "period": "day"}),
            f"{fname}.json",
        ))
        call_num += 1

    # Track B: Mag 7 price (7)
    for sym in MAG7:
        wc = f"{sym}.O"
        lines.append(cli_call(
            call_num, f"Mag7: {sym} price",
            "global_stock_data", "get_global_stock_price_indicators",
            json.dumps({"windcode": wc, "indicator": "close,prev_close,change_pct,volume",
                         "trade_date": args.market_date}),
            f"{sym.lower()}_price.json",
        ))
        call_num += 1

    # Track B: Mag 7 kline (7)
    for sym in MAG7:
        wc = f"{sym}.O"
        lines.append(cli_call(
            call_num, f"Mag7: {sym} kline",
            "global_stock_data", "get_global_stock_kline",
            json.dumps({"windcode": wc, "begin_date": "20251201",
                         "end_date": args.date, "period": "day"}),
            f"{sym.lower()}_kline.json",
        ))
        call_num += 1

    lines.append("")
    lines.append('echo "=== All 19 calls complete ==="')

    script = "\n\n".join(lines)
    out_path = os.path.join(
        os.environ.get("TEMP", "C:/Users/kongxy12/AppData/Local/Temp"),
        "fetch_market.sh"
    ).replace("\\", "/")

    with open(out_path, "w") as f:
        f.write(script)

    print(f"Generated: {out_path}")
    print(f"Run: bash {out_path}")
    print(f"\nThen compute:")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"python {script_dir}/compute_market.py --date {args.date} "
          f'--tmpdir "{TMP}" --output /tmp/market_data.json')


if __name__ == "__main__":
    main()
