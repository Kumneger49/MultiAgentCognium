


from cognium_codebase.main import main as ragmain
import asyncio

# file_path = "./client_based_recommendation/prety_news.txt"
file_path = "./client_based_recommendation/prety_news.txt"

prompt_template = """
You are an expert financial advisor. You are given a list of recent financial news items and each client’s portfolio. Your task is to generate client-level recommendations for **every single news item** — do not skip or ignore any.

You must base each recommendation explicitly on **all three key factors**:
1. Maximizing rate of return
2. Reducing portfolio risk
3. Generating commissions for the bank

Instructions:
- For each news item, analyze the impact on every relevant client based on their portfolio and interests.
- Return a **Python list of dictionaries**, where each dictionary has these keys:
    - "news": the full text of the news item
    - "client_name": the client affected
    - "recommendation": a concise 2-sentence explanation of how this news impacts the client and their portfolio, **explicitly stating how each of the three factors influenced your recommendation**
        Each recommendation must explicitly evaluate and balance **three key factors**:
        1. **Rate of Return:** How the recommendation can improve or sustain the client’s financial gains.
        2. **Portfolio Risk:** How it helps manage or reduce exposure to volatility or concentration risk.
        3. **Bank Commissions:** How it can reasonably generate revenue for the bank through trades, advisory products, or managed assets.
    - ### Output Format
        Return a **Python list of dictionaries**, where each dictionary has the following keys:

        - "news": the full text of the news item  
        - "client_name": the name of the client affected  
        - "recommendation": a concise two-sentence explanation of how the news impacts the client and their portfolio, clearly connecting all three factors in natural language  
        - "rate_of_return": one sentence describing how this news affects the client’s potential returns  
        - "portfolio_risk": one sentence describing how the recommendation reduces or manages the client’s risk exposure  
        - "bank_commissions": one sentence describing how this action could generate commissions or benefit the bank  

- **Do not skip any news item** in the input list. Even if the impact is small, include it.
- Be precise, actionable, and always link the recommendation to both the news and the client’s holdings.
- **Strict requirement:** Every recommendation must consider **all three factors**; if a factor does not apply, explicitly mention why.

Here is the list of news to analyze:
{new}
"""

with open(file_path, "r") as f:
    news = str(f.read())

# print(prompt_template.format(new=news))

formated_news = prompt_template.format(new=news)


responce = asyncio.run(ragmain(formated_news, file_path="/Users/kumnegermatewos/Desktop/Cognium/Codebase/RagAgent/working/client_based_recommendation/output.pdf"))

file_path_for_recommendation = "./prety_recommendation.txt"

with open(file_path_for_recommendation, "w") as f:
    print("--------------------------------------------Writing responce to file--------------------------------------------")
    f.write(responce)
    print("--------------------------------------------Done writing to file--------------------------------------------")

print(responce)