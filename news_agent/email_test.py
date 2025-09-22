from datetime import datetime
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import urllib.parse
import re
import html as htmllib

def get_ticker_news(ticker: str, limit: int = 10) -> None:
    qs = urllib.parse.urlencode({
        "s": ticker,
        "region": "US",
        "lang": "en-US",
    })
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        xml_bytes = resp.read()
    root = ET.fromstring(xml_bytes)
    channel_title = root.findtext("./channel/title") or ""
    count = 0
    for item in root.iterfind(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        desc_html = item.findtext("description") or ""
        desc = _clean_html_text(desc_html)
        try:
            date = parsedate_to_datetime(pub).strftime("%Y-%m-%d") if pub else ""
        except Exception:
            date = pub
        print(f"{date} | {channel_title} | {title} | {link}")
        if desc:
            print(f"    - {desc}")
        count += 1
        if count >= limit:
            break


def _clean_html_text(text: str) -> str:
    if not text:
        return ""
    # Remove HTML tags
    plain = re.sub(r"<[^>]+>", " ", text)
    # Unescape entities
    plain = htmllib.unescape(plain)
    # Collapse whitespace
    plain = re.sub(r"\s+", " ", plain).strip()
    # Truncate to a reasonable length
    if len(plain) > 350:
        plain = plain[:347] + "..."
    return plain


def get_news_for_symbols(symbols: list, limit: int = 5) -> dict:
    out = {}
    for symbol in symbols:
        out[symbol] = get_ticker_news(symbol, limit=limit)
    return out


def print_indexes_news():
    indexes = ["INFY.NS","TM","SPY","AAPL","TSLA", "BND", "AGG", "GLD", "EEM", "IAU", "SIE.DE", "IGLS.L", "MSFT"]
    names = {
        "^GSPC": "S&P 500",
        "^DJI": "Dow Jones",
        "^IXIC": "Nasdaq Composite",
    }
    for symbol in indexes:
        label = names.get(symbol, symbol)
        print(f"\n=== {label} ({symbol}) ===")
        get_ticker_news(symbol, limit=5)
    
    # # Also include selected tickers
    # tickers = ["AAPL", "TSLA"]
    # for symbol in tickers:
    #     print(f"\n=== {symbol} ===")
    #     get_ticker_news(symbol, limit=5)

# Example:
print_indexes_news()