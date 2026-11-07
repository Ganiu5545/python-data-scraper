#!/usr/bin/env python3
"""
sample_scraper.py — fetch the live BNB and BTC price and write a timestamped
report to prices.txt.

    python3 sample_scraper.py                     # write ./prices.txt
    python3 sample_scraper.py --out /tmp/p.txt    # write somewhere else
    python3 sample_scraper.py --api-url http://127.0.0.1:9/nope   # demo the error path

Exit codes:  0 = prices written   1 = API failed, error logged, file untouched
"""

import argparse, json, logging, os, sys, tempfile, urllib.error, urllib.request
from datetime import datetime, timezone

PRIMARY_API = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=binancecoin,bitcoin&vs_currencies=usd&include_24hr_change=true"
)
# CoinGecko rate-limits anonymous callers, so one mirror keeps the sample running.
FALLBACK_API = "https://api.binance.com/api/v3/ticker/24hr?symbols=%5B%22BNBUSDT%22%2C%22BTCUSDT%22%5D"
USER_AGENT = "sample-scraper/1.0 (client demo)"
TIMEOUT = 15

COINS = [("BNB", "binancecoin", "BNBUSDT"), ("BTC", "bitcoin", "BTCUSDT")]

log = logging.getLogger("scraper")


def setup_logging(log_path):
    """Errors go to stderr and to a log file — never into prices.txt."""
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (logging.StreamHandler(sys.stderr), logging.FileHandler(log_path)):
        handler.setFormatter(fmt)
        log.addHandler(handler)


def http_get_json(url):
    """GET url and decode JSON. Raises on any network or decode problem."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} from {url}")
        return json.loads(response.read().decode("utf-8"))


def parse_coingecko(payload):
    return {
        "BNB": {"usd": payload["binancecoin"]["usd"], "change": payload["binancecoin"].get("usd_24h_change")},
        "BTC": {"usd": payload["bitcoin"]["usd"], "change": payload["bitcoin"].get("usd_24h_change")},
    }


def parse_binance(payload):
    rows = {row["symbol"]: row for row in payload}
    result = {}
    for symbol, _cg_id, pair in COINS:
        row = rows[pair]
        result[symbol] = {"usd": float(row["lastPrice"]), "change": float(row["priceChangePercent"])}
    return result


def fetch_prices(api_url, fallback_url=FALLBACK_API):
    """Try the primary API, then the fallback. Returns (prices, source)."""
    try:
        return parse_coingecko(http_get_json(api_url)), "coingecko"
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, RuntimeError) as exc:
        log.warning("primary API failed (%s: %s) — trying fallback", type(exc).__name__, exc)
    return parse_binance(http_get_json(fallback_url)), "binance"


def render(prices, source):
    """Build the human-readable report. One block, easy to paste into a client update."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [f"Prices — {stamp}", f"Source: {source}", ""]
    for symbol, _cg_id, _pair in COINS:
        row = prices[symbol]
        change = row.get("change")
        change_text = f"{change:+.2f}% (24h)" if isinstance(change, (int, float)) else "n/a (24h)"
        lines.append(f"{symbol:>4}  {'$' + format(row['usd'], ',.2f'):>14}   {change_text}")
    return "\n".join(lines) + "\n"


def write_atomically(path, text):
    """Write to a temp file then replace, so a crash can't leave a half-written report."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".prices-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp_path, 0o644)  # mkstemp is 0600; a report should be readable
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch BNB and BTC prices into a timestamped text file.")
    parser.add_argument("--out", default="prices.txt", help="report path (default: prices.txt)")
    parser.add_argument("--log", default="scraper.log", help="error log path (default: scraper.log)")
    parser.add_argument("--api-url", default=PRIMARY_API, help="override the primary API URL")
    parser.add_argument("--fallback-url", default=FALLBACK_API, help="override the fallback API URL")
    args = parser.parse_args(argv)

    setup_logging(args.log)

    try:
        prices, source = fetch_prices(args.api_url, args.fallback_url)
        report = render(prices, source)
        write_atomically(args.out, report)
    except Exception as exc:  # noqa: BLE001 — the point of the sample is that this never crashes
        log.error("could not write prices: %s: %s", type(exc).__name__, exc)
        return 1

    log.info("wrote %s (%s)", args.out, source)
    print(report, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
