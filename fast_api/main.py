from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware



import json
app = FastAPI()


# Allow React frontend (localhost:3000) to access API

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:5173", "http://localhost:3000"],  # 👈 in dev, allow all. In prod, restrict this.
    allow_origins=["*"],  # 👈 in dev, allow all. In prod, restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


file_path = "./prety_news.txt"

with open(file_path, "r") as f:
    # text = f.read()
    text = json.load(f)

def add():
    edited_text = []
    for a in text:
        b = {"ticker": a["ticker"], "headline": a["title"], "summary": a["summary"], "link": a["link"], "sentiment": a["sentiment_score"], "tag": a["tag"]}
        edited_text.append(b)
    return edited_text

@app.get("/")
async def root():

    return add()

@app.get("/g")
def g():
    return "there is nothing here"