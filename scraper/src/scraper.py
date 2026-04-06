
import requests
import json
import os
import base64
import argparse
import boto3
from datetime import datetime, timezone
from dotenv import load_dotenv
from items import ITEMS

load_dotenv()


# eBay credentials and environment
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID", "YOUR_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
# 'sandbox' or 'production'
EBAY_ENV = os.getenv("EBAY_ENV", "production").lower()

# Set eBay API URLs based on environment
if EBAY_ENV == "sandbox":
    EBAY_OAUTH_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    EBAY_BROWSE_URL = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
else:
    EBAY_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    EBAY_BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

# Serper.dev credentials
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "YOUR_SERPER_API_KEY")


def get_application_token():
    """
    eBay requires an OAuth 2.0 Client Credentials grant token 
    to use the Browse API.
    """
    url = EBAY_OAUTH_URL

    # Credentials must be Base64 encoded: "ClientID:ClientSecret"
    auth_str = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {b64_auth}"
    }

    payload = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }

    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"Failed to get token: {response.text}")
        return None


def search_ebay_products(token, query):
    """
    Uses the Browse API to find items.
    """
    # eBay API endpoint for searching items
    url = EBAY_BROWSE_URL

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    params = {
        "q": query,
        "limit": 10,
        "filter": "conditions:{NEW}"  # Ensuring we get new electronics
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json().get("itemSummaries", [])
    else:
        print(f"Error searching eBay: {response.text}")
        return []


def search_serper_products(api_key, query):
    """
    Uses Serper.dev API to search for products (Google Shopping).
    API docs: https://serper.dev/
    """
    url = "https://google.serper.dev/shopping"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {"q": query}
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("shopping", [])
    else:
        print(f"Error searching Serper.dev: {response.text}")
        return []


def normalize_ebay(item, query, scrape_date):
    # eBay Browse API sometimes includes 'itemWebUrl', 'title', 'price', etc.
    # For rating, check for 'rating' or 'reviewRating' fields if present, else None
    rating = None
    rating_count = None
    if 'reviewRating' in item:
        # eBay's reviewRating is an object with 'averageRating' and 'reviewCount'
        rating = item['reviewRating'].get('averageRating')
        rating_count = item['reviewRating'].get('reviewCount')
    elif 'rating' in item:
        rating = item['rating']
    elif 'stars' in item:
        rating = item['stars']
    if 'ratingCount' in item:
        rating_count = item['ratingCount']
    # Extract description, condition, and buying options if available
    description = item.get("shortDescription") or item.get("description")
    condition = item.get("condition")
    buying_options = item.get(
        "buyingOptions") if "buyingOptions" in item else item.get("buyingOption")
    return {
        "productId": item.get("itemId"),
        "site": "ebay",
        "query": query,
        "scrapeDate": scrape_date,
        "name": item.get("title"),
        "price": item.get("price", {}).get("value"),
        "currency": item.get("price", {}).get("currency"),
        "description": description,
        "condition": condition,
        "buyingOptions": buying_options,
        "url": item.get("itemWebUrl"),
        "rating": rating,
        "ratingCount": rating_count
    }


def normalize_serper(item, query, scrape_date):
    # Serper.dev shopping API may include 'rating', 'stars', or similar fields
    rating = item.get("rating")
    if rating is None:
        rating = item.get("stars")
    rating_count = item.get("ratingCount")
    if rating_count is None:
        rating_count = item.get("reviews")
    if rating_count is None:
        rating_count = item.get("reviewCount")
    description = item.get("description")

    return {
        "productId": item.get("productId", item.get("link")),
        "site": "serper",
        "query": query,
        "scrapeDate": scrape_date,
        "name": item.get("title"),
        "price": item.get("price"),
        "currency": item.get("currency"),
        "description": description,
        "url": item.get("link"),
        "rating": rating,
        "ratingCount": rating_count
    }


def upload_to_s3(local_file, bucket, s3_key):
    s3 = boto3.client("s3")
    try:
        s3.upload_file(local_file, bucket, s3_key)
        print(f"Successfully uploaded {local_file} to s3://{bucket}/{s3_key}")
    except Exception as e:
        print(f"Failed to upload {local_file} to S3: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape product data from eBay or Serper.")
    parser.add_argument(
        "mode", choices=["ebay", "serper"], help="Scraper mode: 'ebay' or 'serper'")
    parser.add_argument("items", nargs="+", help="List of items to search for")
    parser.add_argument(
        "--s3-bucket", help="S3 bucket name to upload results. Falls back to S3_BUCKET env var.")
    args = parser.parse_args()

    os.makedirs("../data/scraper", exist_ok=True)

    mode = args.mode
    items = ITEMS if not args.items else args.items
    s3_bucket = args.s3_bucket or os.getenv("S3_BUCKET")
    scrape_date = datetime.now(timezone.utc).isoformat()

    if mode == "ebay":
        print("Requesting OAuth token from eBay...")
        token = get_application_token()
        if not token:
            print("Could not proceed without a valid token.")
            return
        for query in items:
            print(f"Searching eBay for: {query}")
            raw_results = search_ebay_products(token, query)
            formatted_products = [normalize_ebay(
                item, query, scrape_date) for item in raw_results]
            filename = f"../data/scraper/{query.replace(' ', '_')}_ebay.json"
            with open(filename, "w") as f:
                json.dump(formatted_products, f, indent=4)
            print(f"Saved {len(formatted_products)} items to {filename}")
            if s3_bucket:
                upload_to_s3(filename, s3_bucket,
                             f"scraper/{os.path.basename(filename)}")
    elif mode == "serper":
        api_key = SERPER_API_KEY
        if not api_key or api_key == "YOUR_SERPER_API_KEY":
            print("Missing or invalid SERPER_API_KEY in .env")
            return
        for query in items:
            print(f"Searching Serper.dev for: {query}")
            raw_results = search_serper_products(api_key, query)
            formatted_products = [normalize_serper(
                item, query, scrape_date) for item in raw_results]
            filename = f"../data/scraper/{query.replace(' ', '_')}_serper.json"
            with open(filename, "w") as f:
                json.dump(formatted_products, f, indent=4)
            print(f"Saved {len(formatted_products)} items to {filename}")
            if s3_bucket:
                upload_to_s3(filename, s3_bucket,
                             f"scraper/{os.path.basename(filename)}")


if __name__ == "__main__":
    main()
