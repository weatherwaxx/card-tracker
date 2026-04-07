"""
Card Tracker — Trend Detector
=============================
Detects 7-day price trends, price spikes/drops, and low-inventory situations.
"""

from database import get_snapshots, get_latest_snapshots
from config import ALERT_THRESHOLD_PERCENT, LOW_INVENTORY_THRESHOLD


def detect_trends(player):
    """
    Compare the most recent price snapshot to the 7-day average.
    Returns a dict with trend info, or None if not enough data.
    """
    snapshots = get_snapshots(player, days=30)

    if len(snapshots) < 2:
        return None

    latest = snapshots[0]
    latest_avg = latest["avg_price"]

    # Calculate 7-day rolling average from older snapshots
    older_snapshots = snapshots[1:8]  # up to 7 previous days
    if not older_snapshots:
        return None

    historical_avg = sum(s["avg_price"] for s in older_snapshots) / len(older_snapshots)

    if historical_avg == 0:
        return None

    percent_change = ((latest_avg - historical_avg) / historical_avg) * 100

    trend = {
        "player": player,
        "current_avg": round(latest_avg, 2),
        "historical_avg": round(historical_avg, 2),
        "percent_change": round(percent_change, 2),
        "direction": "up" if percent_change > 0 else "down",
        "alert": abs(percent_change) >= ALERT_THRESHOLD_PERCENT,
        "num_data_points": len(older_snapshots),
    }

    return trend


def detect_low_inventory(player):
    """
    Check if a player's active listing count has dropped below threshold.
    Returns a dict with inventory info, or None if no data.
    """
    snapshots = get_snapshots(player, days=7)

    if not snapshots:
        return None

    latest = snapshots[0]
    current_count = latest.get("num_listings", 0)

    if current_count >= LOW_INVENTORY_THRESHOLD:
        return None

    # Calculate average listing count from previous days for context
    older = snapshots[1:8]
    prev_avg_count = None
    if older:
        counts = [s.get("num_listings", 0) for s in older]
        prev_avg_count = round(sum(counts) / len(counts))

    return {
        "player": player,
        "current_listings": current_count,
        "previous_avg_listings": prev_avg_count,
        "threshold": LOW_INVENTORY_THRESHOLD,
        "current_avg_price": round(latest["avg_price"], 2),
    }


def get_all_trends(players):
    """Get trend data for all players. Returns list of trend dicts."""
    trends = []
    for player in players:
        trend = detect_trends(player)
        if trend:
            trends.append(trend)
    return trends


def get_alerts(players):
    """Get only the trends that trigger a price alert (15%+ move)."""
    trends = get_all_trends(players)
    return [t for t in trends if t.get("alert")]


def get_price_spikes(players):
    """Get players with 15%+ price increase."""
    trends = get_all_trends(players)
    return [t for t in trends if t.get("alert") and t["direction"] == "up"]


def get_price_drops(players):
    """Get players with 15%+ price decrease."""
    trends = get_all_trends(players)
    return [t for t in trends if t.get("alert") and t["direction"] == "down"]


def get_low_inventory_alerts(players):
    """Get players with fewer than LOW_INVENTORY_THRESHOLD active listings."""
    alerts = []
    for player in players:
        result = detect_low_inventory(player)
        if result:
            alerts.append(result)
    return alerts


def get_daily_digest(players):
    """
    Generate a full daily digest with all three alert types.
    Returns a dict with spikes, drops, low_inventory, and summary stats.
    """
    trends = get_all_trends(players)
    spikes = [t for t in trends if t.get("alert") and t["direction"] == "up"]
    drops = [t for t in trends if t.get("alert") and t["direction"] == "down"]
    low_inventory = get_low_inventory_alerts(players)

    return {
        "spikes": spikes,
        "drops": drops,
        "low_inventory": low_inventory,
        "all_trends": trends,
        "total_alerts": len(spikes) + len(drops) + len(low_inventory),
    }
