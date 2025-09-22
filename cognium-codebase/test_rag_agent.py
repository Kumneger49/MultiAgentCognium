

from main import main
import asyncio


# print("This is the testing file calling the main file")
# print(asyncio.run(main(query="what is the summary of the document I provided?", file_path="data/RockefellerData.pdf")))
# user_query = "Could you explain the balance sheet of mmlp and give me insights to me as an investment assisant?"
question = f"""
You are a financial assistant agent. Your task is to read structured client records (from PDF text) and produce a rich, structured summary for each client. The summary must be useful for identifying relevant companies, tickers, industries, and regions for news and event extraction.

Follow these rules:

Parse every client record separately.

Extract and summarize in a structured format:

Client Overview: client_id, name, age, nationality, residency_country, segment.

KYC & Risk: source_of_wealth, PEP status, AML risk score, FATCA/CRS, risk_profile, risk_capacity, risk_tolerance.

Goals: primary goal, horizon, target amount, currency.

Portfolio Summary: total value, currency, allocation breakdown (% in equity, fixed income, alternatives, cash, ESG flag).

Holdings List: each holding with ticker, company/asset type, sector/region, currency, market value.

Insights: high-level interpretation (e.g., client is growth-focused with exposure to APAC equities and US government bonds).

Ensure holdings are clearly extractable for downstream news agents (tickers, industries, and regions must be explicit).

Do not omit any company, ticker, or instrument.

Be concise but information-rich. and use private_bank_clients_100.pdf file to get the crusial informations. 
"""


print(asyncio.run(main(question, file_path="data/private_bank_clients_100.pdf")))
# print(asyncio.run(main(query="who is rockefeller writing these letters for?")))