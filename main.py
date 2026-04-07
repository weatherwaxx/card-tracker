"""
Card Tracker — Daily Runner
=============================
Fetches eBay prices for your watchlist, saves to database,
detects 7-day trends, and sends alerts for big price moves.

Run manually:  python main.py
Or schedule via launchd for daily auto-runs.
"""

import json
import os
from datetime import datetime
from database import init_db, save_snapshot, save_listings
from ebay_fetcher import fetch_active_bin_listings, calculate_stats
from trend_detector import get_alerts
from notifier import send_alerts


def load_watchlist():
    """Load the player watchlist from watchlist.json."""
    watchlist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")
    with open(watchlist_path, "r") as f:
        return json.load(f)


def run():
    """Main daily run: fetch prices, save to DB, check trends, send alerts."""
    print(f"\n{'='*50}")
    print(f"Card Tracker — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    # Initialize database
    init_db()

    # Load watchlist
    watchlist = load_watchlist()
    print(f"Tracking {len(watchlist)} players:\n")

    all_players = []

    for entry in watchlist:
        player = entry["player"]
        query = entry["query"]
        all_players.append(player)

        print(f"Fetching: {player}...")

        # Fetch active BIN listings from eBay.ca
        listings = fetch_active_bin_listings(query)

        if not listings:
            print(f"  No listings found for {player}.\n")
            continue

        # Calculate stats
        stats = calculate_stats(listings)
        if not stats:
            print(f"  Could not calculate stats for {player}.\n")
            continue

        print(f"  Found {stats['num_listings']} active listings")
        print(f"  Avg: ${stats['avg_price']:.2f} CAD | Median: ${stats['median_price']:.2f} CAD")
        print(f"  Range: ${stats['min_price']:.2f} - ${stats['max_price']:.2f} CAD\n")

        # Save to database
        save_snapshot(
            player,
            stats["avg_price"],
            stats["median_price"],
            stats["min_price"],
            stats["max_price"],
            stats["num_listings"],
        )
        save_listings(player, listings)

    # Check for trends and send alerts
    print(f"\n{'='*50}")
    print("Checking trends...")
    alerts = get_alerts(all_players)

    if alerts:
        print(f"\n{len(alerts)} alert(s) triggered!")
        for a in alerts:
            direction = "UP" if a["direction"] == "up" else "DOWN"
            print(f"  {a['player']}: {direction} {abs(a['percent_change']):.1f}%")
        send_alerts(alerts)
    else:
        print("No significant price movements detected.")
        if len(all_players) > 0:
            print("(Need at least 2 days of data before trends can be calculated)")

    print(f"\nDone! Run again tomorrow for trend tracking.")
    print(f"View your dashboard at: http://localhost:5050\n")


if __name__ == "__main__":
    run()
