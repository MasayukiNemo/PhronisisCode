"""Yahoo Finance chart API から日足OHLCを取得しCSV保存する。

API: https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=..&interval=1d
User-Agent ヘッダ必須。取得失敗時は握りつぶさず例外送出。
frankfurter.app による daily close クロスチェック関数付き。
"""
import json
import os
import sys
import urllib.request

SYMBOLS = ["EURUSD=X", "USDJPY=X"]
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={rng}&interval=1d"
UA = {"User-Agent": "Mozilla/5.0 (compatible; goldmine-bt/1.0)"}
RANGE_DEFAULT = "5y"


def fetch_chart(symbol, rng=RANGE_DEFAULT, timeout=30):
    url = YAHOO_URL.format(symbol=symbol, rng=rng)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise RuntimeError("Yahoo fetch failed: %s HTTP %s" % (symbol, resp.status))
            raw = resp.read().decode("utf-8")
    except Exception as e:
        raise RuntimeError("Yahoo fetch failed for %s: %s" % (symbol, e)) from e
    try:
        payload = json.loads(raw)
    except Exception as e:
        raise RuntimeError("Yahoo response is not JSON for %s: %s" % (symbol, e)) from e
    return payload


def parse_chart(payload, symbol):
    """Yahoo chart JSON -> list of dict(date,open,high,low,close,volume). 決定的 (同入力->同出力)."""
    try:
        result = payload["chart"]["result"][0]
        ts = result["timestamp"]
        q = result["indicators"]["quote"][0]
    except Exception as e:
        raise RuntimeError("Yahoo payload shape unexpected for %s: %s" % (symbol, e)) from e
    rows = []
    for i, t in enumerate(ts):
        o = (q["open"] or [None])[i] if i < len(q.get("open") or []) else None
        h = (q["high"] or [None])[i] if i < len(q.get("high") or []) else None
        lo = (q["low"] or [None])[i] if i < len(q.get("low") or []) else None
        c = (q["close"] or [None])[i] if i < len(q.get("close") or []) else None
        v = (q["volume"] or [None])[i] if i < len(q.get("volume") or []) else None
        if c is None:
            continue
        import datetime
        dt = datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc).date().isoformat()
        rows.append({"date": dt, "open": o, "high": h, "low": lo, "close": c, "volume": v})
    rows.sort(key=lambda r: r["date"])
    return rows


def save_csv(rows, path):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume"])
        w.writeheader()
        w.writerows(rows)


def frankfurter_close(date_str, base, quote, timeout=30):
    """frankfurter.app による daily close 取得。例: frankfurter_close('2024-01-02','EUR','USD').

    ネット取得のみ。失敗時は RuntimeError (握りつぶし禁止)。
    """
    url = "https://api.frankfurter.app/%s?from=%s&to=%s" % (date_str, base, quote)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise RuntimeError("frankfurter HTTP %s" % resp.status)
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError("frankfurter fetch failed (%s %s/%s): %s" % (date_str, base, quote, e)) from e
    try:
        return float(data["rates"][quote])
    except Exception as e:
        raise RuntimeError("frankfurter payload unexpected: %s" % e) from e


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    rng = sys.argv[1] if len(sys.argv) > 1 else RANGE_DEFAULT
    for sym in SYMBOLS:
        print("fetch %s range=%s" % (sym, rng), flush=True)
        payload = fetch_chart(sym, rng)
        rows = parse_chart(payload, sym)
        if not rows:
            raise RuntimeError("no rows parsed for %s (data empty)" % sym)
        out = os.path.join(base, "%s.csv" % sym)
        save_csv(rows, out)
        print("saved %s (%d rows)" % (out, len(rows)), flush=True)


if __name__ == "__main__":
    main()
