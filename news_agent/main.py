from datetime import datetime
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import urllib.parse
import re
import html as htmllib

def get_ticker_news(ticker: str, limit: int = 10) -> list:
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
    results = []
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
        results.append({
            "date": date,
            "publisher": channel_title,
            "title": title,
            "link": link,
            "summary": desc,
        })
        count += 1
        if count >= limit:
            break
    return results


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
    return {symbol: get_ticker_news(symbol, limit=limit) for symbol in symbols}


 # Example (manual print run):
def main():
    batch = get_news_for_symbols(["INFY.NS","TM","SPY","AAPL","TSLA","BND","AGG","GLD","EEM","IAU","SIE.DE","IGLS.L","MSFT"], limit=3)
    return batch

if __name__ == "__main__":
    print(main())


 