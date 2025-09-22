# import sys
# import requests


# def _format_date(s: str) -> str:
#     try:
#         if s.isdigit() and len(s) == 14:  # GDELT seendate: YYYYMMDDHHMMSS
#             from datetime import datetime
#             return datetime.strptime(s, "%Y%m%d%H%M%S").strftime("%Y-%m-%d")
#     except Exception:
#         pass
#     return s


# def get_news(keyword: str):
#     url = "https://api.gdeltproject.org/api/v2/doc/doc"
#     q = f'("{keyword}") sourcelang:English'
#     params = {
#         "query": q,
#         "mode": "artlist",
#         "format": "json",
#         "maxrecords": 10,
#         "timespan": "7d",
#         "sort": "datedesc",
#     }
#     resp = requests.get(url, params=params, timeout=15)
#     data = resp.json()
#     if resp.status_code != 200:
#         print(f"ERROR: API returned {resp.status_code}")
#         return []
#     articles = data.get("articles", []) or []
#     results = []
#     for a in articles:
#         results.append({
#             "date": _format_date(a.get("seendate", "")),
#             "source": a.get("sourceDomain", ""),
#             "title": a.get("title", ""),
#             "url": a.get("url", ""),
#         })
#     return results


# if __name__ == "__main__":
#     keyword = " ".join(sys.argv[1:]).strip() or "Tesla"
#     items = get_news(keyword)
#     if not items:
#         print(f"No articles found for '{keyword}'.")
#         raise SystemExit(0)
#     for it in items:
#         print(f"{it['date']} | {it['source']} | {it['title']} | {it['url']}")
 

from news_agent.email_test import get_ticker_news, get_news_for_symbols
batch = get_news_for_symbols(["INFY.NS","TM","SPY","AAPL","TSLA", "BND", "AGG", "GLD", "EEM", "IAU", "SIE.DE", "IGLS.L", "MSFT"], limit=1)
print(batch)  
 