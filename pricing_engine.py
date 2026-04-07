"""
Card Tracker — Pricing Engine
==============================
Calculates suggested card prices based on active eBay.ca listing data.

Note: eBay's Browse API only provides active (not sold) listings.
We use active listing data to calculate competitive pricing:
  - Low price (25th %ile) = what to price at to sell quickly
  - Market price (median) = typical asking price you're competing against
  - Suggested price = slightly below median to be competitive
"""

from ebay_fetcher import fetch_active_bin_listings


def _calculate_percentile(prices, percentile):
    """
    Calculate a percentile value from a list of prices.

    Args:
        prices (list): List of numeric prices (will be sorted internally)
        percentile (int): Percentile to calculate (e.g., 25, 50, 75)

    Returns:
        float: The percentile value, rounded to 2 decimal places.
               Returns 0.0 if prices list is empty.
    """
    if not prices:
        return 0.0

    prices_sorted = sorted(prices)
    index = int((percentile / 100.0) * len(prices_sorted))
    index = min(index, len(prices_sorted) - 1)  # Clamp to valid range

    return round(prices_sorted[index], 2)


def suggest_price(year, brand, player, parallel=None, card_number=None, insert=None):
    """
    Suggest a competitive selling price for a football card based on
    what's currently listed on eBay.ca.

    Strategy:
      - Pull active Buy It Now listings for the card
      - Calculate the 25th percentile ("quick sale" price)
      - Calculate the median ("market" price)
      - Suggest pricing at the 40th percentile — competitive but not giving it away
      - Apply shipping logic based on the final price

    Args:
        year (str): Card year (e.g., "2024")
        brand (str): Card brand (e.g., "Prizm", "Mosaic", "Select")
        player (str): Player name (e.g., "Travis Hunter", "Mahomes")
        parallel (str, optional): Parallel/variant (e.g., "Silver", "Gold", "Base")
        card_number (str, optional): Card number within the set (e.g., "101", "RC-1")
        insert (str, optional): Insert or subset name (e.g., "Color Blast", "Rookie")

    Returns:
        dict: Pricing analysis with competitive price, market price, and suggestion.
    """

    # Build the search query from most to least specific
    # We skip "football card" because the eBay category filter (261328)
    # already limits results — adding it narrows too much
    query_parts = [year, brand, player]
    if insert:
        query_parts.append(insert)
    if parallel:
        query_parts.append(parallel)
    if card_number:
        query_parts.append(f"#{card_number}")
    query = " ".join(query_parts)

    # Fetch active Buy It Now listings from eBay.ca
    active_listings = fetch_active_bin_listings(query)

    # Extract prices
    prices = [item["price"] for item in active_listings]

    # Calculate price tiers
    low_price = _calculate_percentile(prices, 25)       # 25th %ile — quick sale price
    market_price = _calculate_percentile(prices, 50)     # Median — typical asking price
    suggested_raw = _calculate_percentile(prices, 40)    # 40th %ile — competitive sweet spot

    # Apply shipping logic to the suggested price
    if suggested_raw > 0 and suggested_raw <= 30:
        shipping_note = "List with free shipping — $1.75 cost built into price"
        suggested_price = round(suggested_raw + 1.75, 2)
    elif suggested_raw > 30:
        shipping_note = "Buyer pays shipping (recommended for cards over $30)"
        suggested_price = round(suggested_raw, 2)
    else:
        shipping_note = "Not enough data to determine shipping strategy"
        suggested_price = 0.0

    return {
        "player": player,
        "query": query,
        "low_price": low_price,
        "market_price": market_price,
        "suggested_price": suggested_price,
        "shipping_note": shipping_note,
        "num_listings": len(active_listings),
    }
