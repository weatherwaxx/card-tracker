"""
Card Pulse — Trend Detector
=============================
Calculates 7-day price trends and triggers alerts at significant moves.
"""

from database import get_snapshots
from config import ALERT_THRESHOLD_PERCENT


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


def get_all_trends(players):
    """Get trend data for all players. Returns list of trend dicts."""
    trends = []
    for player in players:
        trend = detect_trends(player)
        if trend:
            trends.append(trend)
    return trends


def get_alerts(players):
    """Get only the trends that trigger an alert (20%+ move)."""
    trends = get_all_trends(players)
    return [t for t in trends if t.get("alert")]
