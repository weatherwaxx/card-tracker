"""
Card Tracker — eBay Fetcher
============================
Uses eBay's Browse API (the modern replacement for the Finding API)
to pull sold and active Buy It Now listing prices.
Prioritizes Canadian listings (eBay.ca) via marketplace ID.

Requires OAuth2 client credentials (App ID + Client Secret).
"""

import requests
import base64
import time
from config import EBAY_APP_ID, EBAY_CLIENT_SECRET, MAX_SOLD_LISTINGS

# eBay Browse API endpoints
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
BROWSE_API_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

# Cache the OAuth token so we don't request a new one every call
_token_cache = {"token": None, "expires_at": 0}


def _get_oauth_token():
    """
    Get an OAuth2 application access token using client credentials.
    Caches the token and reuses it until it expires.
    """
    # Return cached token if still valid (with 60s buffer)
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    # Encode credentials as Base64 for Basic auth
    credentials = f"{EBAY_APP_ID}:{EBAY_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded}",
    }

    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data, timeout=15)
        response.raise_for_status()
        token_data = response.json()

        _token_cache["token"] = token_data["access_token"]
        _token_cache["expires_at"] = time.time() + token_data.get("expires_in", 7200)

        print("  OAuth token acquired successfully.")
        return _token_cache["token"]

    except requests.exceptions.RequestException as e:
        print(f"  Error getting OAuth token: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return None


def fetch_sold_listings(query, max_results=None):
    """
    Fetch recently sold listings from eBay for a given search query.
    Uses the Browse API with a filter for sold/completed items.

    Args:
        query (str): Search keywords (e.g., "2024 Prizm Travis Hunter")
        max_results (int): Number of results to return. Defaults to MAX_SOLD_LISTINGS.

    Returns:
        list: List of dicts with keys: title, price, sold_date
    """
    if max_results is None:
        max_results = MAX_SOLD_LISTINGS

    token = _get_oauth_token()
    if not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_CA",  # Prioritize Canadian listings
        "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=CA",
    }

    # Browse API uses 'q' for keywords and 'filter' for conditions
    # category_ids 261328 = Football Cards
    params = {
        "q": query,
        "category_ids": "261328",
        "filter": "buyingOptions:{FIXED_PRICE|AUCTION},priceCurrency:CAD,price:[0.99..],conditions:{NEW|LIKE_NEW|VERY_GOOD|GOOD}",
        "sort": "newlyListed",
        "limit": str(min(max_results, 200)),  # Browse API max is 200
    }

    try:
        response = requests.get(BROWSE_API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        items = data.get("itemSummaries", [])
        listings = []

        for item in items:
            title = item.get("title", "")
            price_info = item.get("price", {})
            price = float(price_info.get("value", "0"))
            item_end_date = item.get("itemEndDate", "")

            if price > 0:
                listings.append({
                    "title": title,
                    "price": price,
                    "sold_date": item_end_date,
                })

        print(f"  Browse API returned {len(listings)} listings for: {query}")
        return listings

    except requests.exceptions.RequestException as e:
        print(f"  Error fetching sold listings from eBay: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return []
    except (KeyError, IndexError, ValueError) as e:
        print(f"  Error parsing sold listings response: {e}")
        return []


def fetch_active_bin_listings(query, max_results=None):
    """
    Fetch active Buy It Now (fixed price) listings from eBay.
    Uses the Browse API filtered to fixed-price listings only.

    Args:
        query (str): Search keywords (e.g., "2024 Prizm Travis Hunter")
        max_results (int): Number of results to return. Defaults to MAX_SOLD_LISTINGS.

    Returns:
        list: List of dicts with keys: title, price, listing_date
    """
    if max_results is None:
        max_results = MAX_SOLD_LISTINGS

    token = _get_oauth_token()
    if not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_CA",  # Prioritize Canadian listings
        "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=CA",
    }

    params = {
        "q": query,
        "category_ids": "261328",
        "filter": "buyingOptions:{FIXED_PRICE},priceCurrency:CAD,price:[0.99..]",
        "sort": "price",
        "limit": str(min(max_results, 200)),
    }

    try:
        response = requests.get(BROWSE_API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        items = data.get("itemSummaries", [])
        listings = []

        for item in items:
            title = item.get("title", "")
            price_info = item.get("price", {})
            price = float(price_info.get("value", "0"))
            listing_date = item.get("itemCreationDate", "")

            if price > 0:
                listings.append({
                    "title": title,
                    "price": price,
                    "listing_date": listing_date,
                })

        print(f"  Browse API returned {len(listings)} active BIN listings for: {query}")
        return listings

    except requests.exceptions.RequestException as e:
        print(f"  Error fetching active BIN listings from eBay: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return []
    except (KeyError, IndexError, ValueError) as e:
        print(f"  Error parsing active BIN listings response: {e}")
        return []


def calculate_stats(listings):
    """
    Calculate price statistics from a list of listings.

    Args:
        listings (list): List of dicts with "price" key

    Returns:
        dict: Stats including avg_price, median_price, min_price, max_price, num_listings
              Returns None if listings list is empty.
    """
    if not listings:
        return None

    prices = [l["price"] for l in listings]
    prices.sort()

    avg_price = sum(prices) / len(prices)
    median_price = prices[len(prices) // 2]
    min_price = prices[0]
    max_price = prices[-1]

    return {
        "avg_price": round(avg_price, 2),
        "median_price": round(median_price, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "num_listings": len(prices),
    }
