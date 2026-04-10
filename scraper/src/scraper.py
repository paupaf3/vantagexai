import argparse
import base64
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import boto3
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# eBay credentials and environment
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID", "")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET", "")
EBAY_ENV = os.getenv("EBAY_ENV", "production").lower()

if EBAY_ENV == "sandbox":
    EBAY_OAUTH_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    EBAY_BROWSE_URL = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
else:
    EBAY_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    EBAY_BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

# Serper.dev credentials
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# Output directory: override with SCRAPER_OUTPUT_DIR env var.
# Defaults to <repo_root>/data/scraper for local runs; set to /tmp/scraper in Docker.
_DEFAULT_OUTPUT_DIR = str(Path(__file__).resolve().parent.parent.parent / "data" / "scraper")
OUTPUT_DIR = Path(os.getenv("SCRAPER_OUTPUT_DIR", _DEFAULT_OUTPUT_DIR))


def get_application_token():
    """
    eBay requires an OAuth 2.0 Client Credentials grant token
    to use the Browse API.
    """
    auth_str = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {b64_auth}",
    }
    payload = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }
    try:
        response = requests.post(EBAY_OAUTH_URL, headers=headers, data=payload, timeout=15)
        if response.status_code == 200:
            return response.json().get("access_token")
        logger.error("Failed to get eBay token: %s", response.text)
        return None
    except requests.RequestException as exc:
        logger.error("Network error fetching eBay token: %s", exc)
        return None


def search_ebay_products(token, query):
    """
    Uses the Browse API to find items.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }
    params = {"q": query, "limit": 10, "filter": "conditions:{NEW}"}
    try:
        response = requests.get(EBAY_BROWSE_URL, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            return response.json().get("itemSummaries", [])
        logger.error("Error searching eBay: %s", response.text)
        return []
    except requests.RequestException as exc:
        logger.error("Network error searching eBay: %s", exc)
        return []


def search_serper_products(api_key, query):
    """
    Uses Serper.dev API to search for products (Google Shopping).
    API docs: https://serper.dev/
    """
    url = "https://google.serper.dev/shopping"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json={"q": query}, timeout=15)
        if response.status_code == 200:
            return response.json().get("shopping", [])
        logger.error("Error searching Serper.dev: %s", response.text)
        return []
    except requests.RequestException as exc:
        logger.error("Network error searching Serper.dev: %s", exc)
        return []


def normalize_ebay(item, query, scrape_date):
    rating = None
    rating_count = None
    if "reviewRating" in item:
        # eBay's reviewRating is an object with 'averageRating' and 'reviewCount'
        rating = item["reviewRating"].get("averageRating")
        rating_count = item["reviewRating"].get("reviewCount")
    elif "rating" in item:
        rating = item["rating"]
        rating_count = item.get("ratingCount")
    elif "stars" in item:
        rating = item["stars"]
        rating_count = item.get("ratingCount")

    description = item.get("shortDescription") or item.get("description")
    buying_options = item.get("buyingOptions") or item.get("buyingOption")
    return {
        "productId": item.get("itemId"),
        "site": "ebay",
        "query": query,
        "scrapeDate": scrape_date,
        "name": item.get("title"),
        "price": item.get("price", {}).get("value"),
        "currency": item.get("price", {}).get("currency"),
        "description": description,
        "condition": item.get("condition"),
        "buyingOptions": buying_options,
        "url": item.get("itemWebUrl"),
        "rating": rating,
        "ratingCount": rating_count,
    }


def normalize_serper(item, query, scrape_date):
    rating = item.get("rating") or item.get("stars")
    rating_count = item.get("ratingCount") or item.get("reviews") or item.get("reviewCount")
    return {
        "productId": item.get("productId", item.get("link")),
        "site": "serper",
        "query": query,
        "scrapeDate": scrape_date,
        "name": item.get("title"),
        "price": item.get("price"),
        "currency": item.get("currency"),
        "description": item.get("description"),
        "url": item.get("link"),
        "rating": rating,
        "ratingCount": rating_count,
    }


def upload_to_s3(local_file, bucket, s3_key):
    s3 = boto3.client("s3")
    try:
        s3.upload_file(str(local_file), bucket, s3_key)
        logger.info("Uploaded %s to s3://%s/%s", local_file, bucket, s3_key)
    except Exception as exc:
        logger.error("Failed to upload %s to S3: %s", local_file, exc)


def _safe_filename(query: str) -> str:
    """Sanitize query string for use as a filename."""
    return re.sub(r"[^\w\-]", "_", query)


def _deduplicate(products: list) -> list:
    """Remove duplicate records by productId within a single query result."""
    seen = set()
    result = []
    for item in products:
        pid = item.get("productId")
        if pid not in seen:
            seen.add(pid)
            result.append(item)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Scrape product data from eBay or Serper.")
    parser.add_argument(
        "mode", choices=["ebay", "serper"], help="Scraper mode: 'ebay' or 'serper'")
    parser.add_argument("items", nargs="+", help="List of items to search for")
    parser.add_argument(
        "--s3-bucket", help="S3 bucket name to upload results. Falls back to S3_BUCKET env var.")
    args = parser.parse_args()

    mode = args.mode
    items = args.items
    s3_bucket = args.s3_bucket or os.getenv("S3_BUCKET")
    scrape_date = datetime.now(timezone.utc).isoformat()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if mode == "ebay":
        if not EBAY_CLIENT_ID or not EBAY_CLIENT_SECRET:
            logger.error("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set.")
            sys.exit(1)
        logger.info("Requesting OAuth token from eBay...")
        token = get_application_token()
        if not token:
            logger.error("Could not obtain a valid eBay token.")
            sys.exit(1)
        for i, query in enumerate(items):
            if i > 0:
                time.sleep(0.5)
            logger.info("Searching eBay for: %s", query)
            raw_results = search_ebay_products(token, query)
            products = _deduplicate(
                [normalize_ebay(item, query, scrape_date) for item in raw_results])
            filename = OUTPUT_DIR / f"{_safe_filename(query)}_ebay.json"
            with open(filename, "w") as f:
                json.dump(products, f, indent=4)
            logger.info("Saved %d items to %s", len(products), filename)
            if s3_bucket:
                upload_to_s3(filename, s3_bucket, f"scraper/{filename.name}")

    elif mode == "serper":
        if not SERPER_API_KEY:
            logger.error("SERPER_API_KEY must be set.")
            sys.exit(1)
        for i, query in enumerate(items):
            if i > 0:
                time.sleep(0.5)
            logger.info("Searching Serper.dev for: %s", query)
            raw_results = search_serper_products(SERPER_API_KEY, query)
            products = _deduplicate(
                [normalize_serper(item, query, scrape_date) for item in raw_results])
            filename = OUTPUT_DIR / f"{_safe_filename(query)}_serper.json"
            with open(filename, "w") as f:
                json.dump(products, f, indent=4)
            logger.info("Saved %d items to %s", len(products), filename)
            if s3_bucket:
                upload_to_s3(filename, s3_bucket, f"scraper/{filename.name}")


if __name__ == "__main__":
    main()
