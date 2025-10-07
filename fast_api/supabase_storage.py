

from supabase import create_client
import os
import json

from dotenv import load_dotenv

# Load variables from .env
load_dotenv()  

# Get these from your Supabase project
SUPABASE_URL = os.getenv("SUPABASE_URL")  # e.g., "https://abcd.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # anon/public key

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_news_file():
    local_file = "../orchestrator/prety_news.txt"
    cloud_file = "prety_news.txt"

    # Read file
    with open(local_file, "r") as f:
        content = f.read()
    content_bytes = content.encode("utf-8")

    bucket = supabase.storage.from_("news-files")

    # Delete existing file if it exists
    try:
        bucket.remove([cloud_file])
    except Exception:
        pass  # ignore if file doesn't exist

    # Upload
    bucket.upload(cloud_file, content_bytes)

    # Get public URL
    url = bucket.get_public_url(cloud_file)
    return url


def main():
    print(upload_news_file())
    print("stored successfully")

if __name__ == "__main__":
    main()




