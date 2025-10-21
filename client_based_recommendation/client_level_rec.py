


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
- For each news item, analyze the impact on **at least two different clients** whose portfolios are affected or potentially influenced by the news.  
  - Select clients whose holdings, interests, or industry exposures make them relevant to the news.  
  - If more than two clients are relevant, include all significant ones.  
  - **Do not skip or omit any news item**, and ensure at least two clients are analyzed for each.

- Return a **Python list of dictionaries**, where each dictionary has these keys:
    - "news": the full text of the news item  
    - "client_name": the name of the client affected  
    - "recommendation": a concise two-sentence explanation of how this news impacts the client and their portfolio, clearly connecting all three factors in natural language  
    - "rate_of_return": one sentence describing how this news affects the client’s potential returns, including a **quantitative estimate** (e.g., "expected return may increase by 3–5%")  
    - "portfolio_risk": one sentence describing how the recommendation reduces or manages the client’s risk exposure, with a **numerical estimate** (e.g., "volatility risk may decline by around 8%")  
    - "bank_commissions": one sentence describing how this action could generate commissions or benefit the bank, with a **quantitative prediction** (e.g., "estimated commission growth of 2–3% from related trades or advisory fees")  

Additional requirements:
- Every recommendation must explicitly evaluate and balance **all three key factors**.  
  - If a factor does not apply, explicitly mention why and assign an estimated 0% change.  
- Use precise, data-driven language that reflects professional financial reasoning.  
- Ensure that **each news item generates recommendations for at least two distinct clients**.  
- Ensure all numerical predictions are realistic (e.g., within ±15% range unless the news is exceptionally significant).

### Output Format:
Return a **Python list of dictionaries**, with one dictionary per (news item, client) pair. Example structure:

[
    {{
        "news": "...",
        "client_name": "...",
        "recommendation": "...",
        "rate_of_return": "...",
        "portfolio_risk": "...",
        "bank_commissions": "..."
    }},
    ...
]

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