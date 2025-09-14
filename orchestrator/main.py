
import asyncio

from news_agent.main import main as newsmain
from cognium_codebase.main import main as ragmain

from datetime import datetime 

news_json = newsmain()['output']
# news_json = "newsmain()['output'] this is fake news"
print("----------------------------output from the news agent-------------------------------\n\n")

print(news_json)

print("\n\n----------------------------ended printing output-------------------------------\n\n")


rag_prompt_template = f"""
You are a financial research assistant (RAG agent). You are given recent news and events about multiple client holdings in the following JSON format:

{news_json}

Your task is to:

1. For each ticker/asset/holding in the JSON, provide **more detailed context and explanation** about the news/events and also the cleints that are interested in the holding and will be affected
2. Explain **how each news item could impact the performance, value, or risk** of the holding.
3. Include any **connections between holdings**, e.g., if news about one company/sector could affect others in the portfolio.
4. Be concise, clear, and actionable. Avoid repeating raw news content—focus on insights.
5. Return the final result as a **plain-text summary suitable for a client**, **not as JSON**. Use bullet points or short paragraphs for readability.
6. Do not include any client-specific identifiers or personal info—only general portfolio implications.

Make sure your response is easy to read for someone interested in understanding the potential effects of these news events on their investments.
"""

print("----------------------------calling the rag agent-------------------------------")

rag_final_answer = asyncio.run(ragmain(rag_prompt_template, 
                                       file_path = "/Users/kumnegermatewos/Desktop/Cognium/Codebase/RagAgent/working/cognium_codebase/data/private_bank_clients_100.pdf"))


output_file = "./orchestrator/output.txt"

with open(output_file, "a") as f:
    print("---------------------------------------------------------------Writing to the log file---------------------------------------------------------------")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write(f"[{now}] This is a tracing message\n")
    f.write(rag_final_answer + "\n----------------------------------------output ends here-------------------------------------------------\n")
    print(f"---------------------------------------------------------------Finished writing to the file that started at {now}---------------------------------------------------------------")

print(rag_final_answer)
# print(asyncio.run(ragmain(question, file_path="data/private_bank_clients_100.pdf")))



# rag_summary = "../cognium_codebase/client_summary.txt"
# news_data = f"{main()}"

# orchestrator_prompt = f"""
# You are a financial orchestrator agent. You are given:

# 1. An aggregated summary of client holdings, portfolio patterns, and key investment properties:
# {rag_summary}

# 2. A structured set of recent news and events affecting these holdings:
# {news_data}

# Your task is to produce a **final, user-friendly summary** that explains:

# - How recent news or events could **impact each holding or asset**.  
# - Key trends, risks, and opportunities for the portfolio.  
# - Practical, actionable insights for a user who owns or is considering these holdings.  

# Follow these guidelines:

# 1. Present the summary in **clear, human-readable paragraphs**, not JSON.  
# 2. For each major holding or asset type, include:
#    - The ticker or company name.
#    - What the news means for its performance or value.
#    - Any implications for clients with similar portfolio patterns (e.g., growth-focused, balanced, risk-averse).  
# 3. Highlight **general portfolio patterns** affected by news, such as sectors or regions experiencing trends.  
# 4. Be concise, informative, and suitable for a user wanting to understand **how their investments may be affected**.

# Example style:

# "NVDA (NVIDIA) has recently reported strong earnings and increasing demand for AI chips, indicating potential growth for technology-focused portfolios. Growth-oriented investors may benefit from increased exposure, while risk-averse clients should monitor market volatility.

# US Government Bonds (US10Y) are seeing rising yields, which may slightly reduce bond prices. Clients with high fixed-income allocations should consider the impact on their portfolios.

# Overall, the client base shows significant exposure to US and APAC equities, with balanced portfolios benefiting from diversification across sectors. Recent news suggests strong opportunities in technology and emerging markets, but rising interest rates could affect fixed-income returns."
# """

