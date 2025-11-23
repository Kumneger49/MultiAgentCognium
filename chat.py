from dotenv import load_dotenv
load_dotenv()


from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = "What is the capital of France?"

response = llm.invoke(prompt)

print(response.content)