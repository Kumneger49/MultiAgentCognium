from langchain.agents import initialize_agent, tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults 
import datetime 


load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini")
search_tool = TavilySearchResults(search_depth="basic", max_results=5, time_range = "week")


@tool
def current_system_time(format: str):
    """This is a tool to know the current data of the system"""
    current_time = datetime.datetime.now()
    return current_time

def main():


    tools = [search_tool, current_system_time]

    search_agent = initialize_agent(llm=llm, tools=tools, agent="zero-shot-react-description", verbose=False, handle_parsing_errors=True, max_iterations=15)

    # company_interest = input("Which company you want the news for?\n")

    # user_prompt = f"""You are an investement advisor that helps me with finding major news that affect the {company_interest} company. make sure you are using the current_sytem_tool to to know the current date, time, and second"""

    with open("cognium_codebase/client_summary.txt", "r") as f:
        summary = f.read()

    news_prompt = f"""
    You are a financial news agent. You are given a summary of private bank client holdings and portfolio patterns as follows:

    {summary}

    Your task is to:

    1. Identify all **relevant companies, tickers, assets, and industries** mentioned in the summary.
    2. First, call the `current_system_time` tool to know today's exact date.
    3. For each company, ticker, or asset, use the `search_tool` to find **only news from the last 30 days** that could impact their value or performance.
    4. Include the **region** and **industry/sector** for context.
    5. Provide a **structured JSON output** listing each ticker/asset, its company or industry, region, and a list of relevant news/events with publication date and source.
    6. Be concise, accurate, and only include news relevant to the holdings or patterns in the summary.
    """



    response = search_agent.invoke(news_prompt)
    return response

if __name__=="__main__":
    print(main())