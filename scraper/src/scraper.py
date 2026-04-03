import requests
import json
import os
import base64
from dotenv import load_dotenv
from items import ITEMS

load_dotenv()

# These will come from your eBay Developer Portal
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID", "YOUR_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET", "YOUR_CLIENT_SECRET")


def get_application_token():
    """
    eBay requires an OAuth 2.0 Client Credentials grant token 
    to use the Browse API.
    """
    url = "https://api.ebay.com/identity/v1/oauth2/token"

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
    # DOCUMENTATION: https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

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


def main():
    os.makedirs("../data/scraper", exist_ok=True)

    print("Requesting OAuth token from eBay...")
    token = get_application_token()

    if not token:
        print("Could not proceed without a valid token.")
        return

    for query in ITEMS:
        print(f"Searching eBay for: {query}")
        raw_results = search_ebay_products(token, query)

        formatted_products = []
        for item in raw_results:
            # Normalizing the data for your VantageX.ai schema
            formatted_products.append({
                "productId": item.get("itemId"),
                "site": "ebay",
                "name": item.get("title"),
                "price": item.get("price", {}).get("value"),
                "currency": item.get("price", {}).get("currency"),
                "description": item.get("shortDescription", f"New {query} on eBay"),
                "url": item.get("itemWebUrl")
            })

        filename = f"../data/scraper/{query.replace(' ', '_')}.json"
        with open(filename, "w") as f:
            json.dump(formatted_products, f, indent=4)

        print(f"Saved {len(formatted_products)} items to {filename}")


if __name__ == "__main__":
    main()
