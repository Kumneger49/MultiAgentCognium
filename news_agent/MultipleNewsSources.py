# import requests
# import json
# from dotenv import load_dotenv

# load_dotenv()
# import os

# EODHD_API_KEY=os.getenv("EODHD_API_KEY")

# def getNews(ticker:str):
#     try:
#         # MARKETAUX
#         # url = f'https://api.marketaux.com/v1/news/all?symbols=AAPL&filter_entities=true&language=en&api_token=xeH2hyArM1Dq4H9X7zVlqqvy0N3yCcd9tn1MyT5L'
#         # EODHD
#         # url = f'https://eodhd.com/api/news?s=AAPL&offset=0&limit=1&from=2023-11-02&to=2025-11-02&api_token={EODHD_API_KEY}&fmt=json'
#         # vantage
#         # url = 'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&limit=1&tickers=AAPL&apikey=DEMO'
#         # perigon
#         url = 'https://api.perigon.io/v1/articles/all?source=cnn.com&sortBy=date&apiKey=731f8576-7509-45af-a239-5409952e2cb0'
#         data = requests.get(url).json()
        

#         print(f"Data for {ticker}: \n{json.dumps(data, indent=4)} and length: {len(data)}")
#     except Exception as e:
#         print(f"throwing error: {e}")



# # tickers = ["INFY.NS","TM","SPY","AAPL","TSLA","BND","AGG","GLD","EEM","IAU","SIE.DE","IGLS.L","MSFT"]
# # for ticker in tickers:
# #     getNews(ticker)
# getNews("AAPL")


"""PERINGAN BASIC API CALLING"""


#!/usr/bin/env python3
"""
Multi-Company Financial News Fetcher using Company Names (Perigon API)
"""

from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime, timedelta
from perigon import ApiClient, V1Api

import json 


def fetch_company_news(api, companies, days=7, per_company_limit=1):
    """Fetch recent descriptive news for companies based on full names"""
    results = {}
    # date_from = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    for ticker, company_name in companies.items():
        print(f"\n🔎 Fetching news for {company_name} ({ticker}) since 2025-10-27...")

        params = {
            "q": f"{company_name}.",
            "var_from": "2025-10-27",
            "to": "2025-11-03",
            "size": 5,
            "source": [
                "cnn.com", "bbc.com", "AlJazeera.com", "theguardian.com",
                "techcrunch.com", "wsj.com", "vox.com", "news.yahoo.com"
            ]
            # "sortBy": "relevance",
            # "lang": "en"
        }

        try:
            articles = api.search_articles(**params)  # Fetch articles for the company

            news_list = []
            for article in articles.articles:
                news_list.append({
                    "title": article.title,
                    "summary": article.summary,
                    "source": article.source.domain if article.source else "Unknown",
                    "published": article.pub_date,
                    "url": article.url
                })

            results[ticker] = news_list
            print(f"✅ Got {len(news_list)} articles for {company_name}")

        except Exception as e:
            print(f"❌ Error fetching news for {company_name}: {e}")
            results[ticker] = []

    return results



def main():
    api_key = os.getenv("PERIGON_API_KEY")
    if not api_key:
        print("❌ Please set your PERIGON_API_KEY environment variable.")
        return

    api = V1Api(ApiClient(api_key=api_key))

    # 🏢 Map tickers to company names
    companies = {
        "INFY.NS": "Infosys Limited",
        "TM": "Toyota Motor Corporation",
        "SPY": "SPDR S&P 500 ETF Trust",
        "AAPL": "Apple Inc.",
        "TSLA": "Tesla Inc.",
        "BND": "Vanguard Total Bond Market ETF",
        "AGG": "iShares Core U.S. Aggregate Bond ETF",
        "GLD": "SPDR Gold Trust",
        "EEM": "iShares MSCI Emerging Markets ETF",
        "IAU": "iShares Gold Trust",
        "SIE.DE": "Siemens AG",
        "IGLS.L": "IG Group Holdings plc",
        "MSFT": "Microsoft Corporation"
    }

    file_path = "news_agent/paregon_news.json"
    with open(file_path, "r") as f:
        response = json.load(f)
    if response == "":
        print("News is not fetched yet------------------------fetching------------------------")
        response = fetch_company_news(api, companies, days=7, per_company_limit=3)
        """Writing to file for a better caching"""
        with open(file_path, 'w') as f:
            json.dump(response, f, indent=4)
        
    else:
        print("News is already fetched------------------------no need to fetch------------------------")
        return response

    

    # returning_news = []

    # # 📰 Display results
    # for ticker, articles in news_data.items():
    #     news = {
    #         "ticker": ticker,
    #     }
    #     # print(f"\n====== {ticker} ======")
    #     if not articles:
    #         print("No recent news found.")
    #         continue
    #     for art in articles:
    #         news["title"] = art['source']
    #         news["Published"] = art['published']
    #         news["Summary"] = art["summary"]
    #         news["URL"] = art['url']
    #     returning_news.append(news)
    # return returning_news


if __name__ == "__main__":
        response = json.dumps(main(), indent=4)
        print(response)

# print("there is no article")