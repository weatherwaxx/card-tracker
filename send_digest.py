"""
Card Tracker — Daily Digest Sender
====================================
Checks today's data for price spikes, drops, and low inventory,
then sends a digest email and desktop notification.

Scheduled to run daily at 5pm PDT via launchd.
Can also be run manually: python send_digest.py
"""

import json
import os
from datetime import datetime
from database import init_db, get_all_players
from trend_detector import get_daily_digest
from notifier import send_daily_digest


def load_watchlist_players():
    """Load player names from watchlist.json."""
    watchlist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")
    with open(watchlist_path, "r") as f:
        watchlist = json.load(f)
    return [entry["player"] for entry in watchlist]


def run():
    """Generate and send the daily digest."""
    print(f"\n{'='*50}")
    print(f"Card Tracker Digest — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    init_db()

    # Use watchlist players + any others in the database
    watchlist_players = load_watchlist_players()
    db_players = get_all_players()
    all_players = list(set(watchlist_players + db_players))
    all_players.sort()

    print(f"Checking {len(all_players)} players for alerts...\n")

    digest = get_daily_digest(all_players)

    # Print summary
    if digest["spikes"]:
        print(f"📈 Price Spikes ({len(digest['spikes'])}):")
        for s in digest["spikes"]:
            print(f"   {s['player']}: +{s['percent_change']:.1f}% (${s['current_avg']:.2f})")

    if digest["drops"]:
        print(f"\n📉 Price Drops ({len(digest['drops'])}):")
        for d in digest["drops"]:
            print(f"   {d['player']}: {d['percent_change']:.1f}% (${d['current_avg']:.2f})")

    if digest["low_inventory"]:
        print(f"\n⚠️  Low Inventory ({len(digest['low_inventory'])}):")
        for li in digest["low_inventory"]:
            print(f"   {li['player']}: only {li['current_listings']} listings")

    if digest["total_alerts"] == 0:
        print("No alerts today — all quiet.")

    print(f"\nSending digest...")
    send_daily_digest(digest)
    print("Done!\n")


if __name__ == "__main__":
    run()
