


"""

We bacially create new pdf documents for each a week or some time interval that contains the interviews with each client in that time interval
then proces each document each time and make it ready for enqueries




i need to find a way to process the new document that contains interview with clients,






i need to extract the quantitative news data for the tickers including but not only the tickers I have,

i need to prompt the rag pipeline to give me suggestions for clients depending on the interview they did and their interestss

basically write a script that finds a trend for what is happening in the market and classify based on the features you get from the financial news
and make a recommendation pipeline based on this news identifacation and clients interests

"""


file_path_to_prety_news = "./client_based_recommendation/prety_news.txt"
news = ""

with open(file_path_to_prety_news, 'r') as f:
    news = f.read()

prompt = f"""You are an AI financial recommendation assistant. Your task is to analyze recent financial news, clients’ current holdings, and their processed interview summaries/notes, and then recommend which assets each client might consider buying. 

This is the recent financial news: {news}

Follow these steps carefully:

1. **Task:**
   - For each client, analyze their holdings, interests, and the summary notes/interviews already processed by the system.
   - Check which news articles are **relevant to the client’s interests** (even if they don’t directly hold the asset).
   - Identify **new assets** (not currently held) that align with their interests and have **positive or negative sentiment**, considering risk/reward potential.
   - Rank recommended new assets in **priority order** (highest potential impact first).
   - **Explicitly reference the client’s summary notes/interview** in your reasoning for each recommendation.
   - Include a brief reasoning for each recommendation, linking it to both the news and the client’s notes.


**Important Notes:**
- Do NOT recommend assets the client already owns.
- Always justify recommendations using **both the news and the client’s summary notes**.
- Prioritize assets that have **high relevance and positive sentiment** in recent news.
- Be concise, precise, and actionable.
"""

from cognium_codebase.main import main as ragmain
import asyncio

rag_output = asyncio.run(ragmain(prompt, file_path="/Users/kumnegermatewos/Desktop/Cognium/Codebase/RagAgent/working/client_based_recommendation/output.pdf"))
print(rag_output)

"""EXTERNAL"""
##################### Get the news data and classify or find a way to make a prediction on which assets or tickers have more edge in the market #####################



##################### prompt engineer the rag pipeline to find clients that might be interested in the new assets whose values got increased in the market #####################



