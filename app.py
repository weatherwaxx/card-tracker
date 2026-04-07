"""
Card Tracker — Flask Web App
=============================
A local Flask web app for Catherine's eBay card store.
Provides pricing tool, market monitoring, watchlist, and price history.

Run with: python app.py
Then visit: http://localhost:5050
"""

from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from markupsafe import Markup
from pricing_engine import suggest_price
from database import init_db, get_latest_snapshots, get_all_players, get_snapshots, save_snapshot, save_listings
from ebay_fetcher import fetch_active_bin_listings, calculate_stats
from trend_detector import detect_trends
import json
import os
import threading
from datetime import datetime, timedelta

app = Flask(__name__)

# Track refresh state
_refresh_lock = threading.Lock()
_refresh_in_progress = False
_last_refresh_check = None


def _data_is_stale():
    """Check if the most recent snapshot is older than 24 hours."""
    try:
        snapshots = get_latest_snapshots()
        if not snapshots:
            return True
        latest_time = max(s["fetched_at"] for s in snapshots)
        latest_dt = datetime.fromisoformat(latest_time)
        return datetime.now() - latest_dt > timedelta(hours=24)
    except Exception:
        return True


def _refresh_watchlist_data():
    """Fetch fresh eBay data for all watchlist players. Runs in background."""
    global _refresh_in_progress
    try:
        watchlist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")
        with open(watchlist_path, "r") as f:
            watchlist = json.load(f)

        init_db()
        for entry in watchlist:
            player = entry["player"]
            query = entry["query"]
            try:
                listings = fetch_active_bin_listings(query)
                if not listings:
                    continue
                stats = calculate_stats(listings)
                if not stats:
                    continue
                save_snapshot(
                    player,
                    stats["avg_price"],
                    stats["median_price"],
                    stats["min_price"],
                    stats["max_price"],
                    stats["num_listings"],
                )
                save_listings(player, listings)
            except Exception:
                continue
    finally:
        with _refresh_lock:
            _refresh_in_progress = False


def _auto_refresh_if_stale():
    """Trigger a background refresh if data is stale and no refresh is running."""
    global _refresh_in_progress, _last_refresh_check

    # Don't check more than once every 5 minutes
    if _last_refresh_check and datetime.now() - _last_refresh_check < timedelta(minutes=5):
        return False

    _last_refresh_check = datetime.now()

    with _refresh_lock:
        if _refresh_in_progress:
            return True  # already refreshing
        if _data_is_stale():
            _refresh_in_progress = True
            thread = threading.Thread(target=_refresh_watchlist_data, daemon=True)
            thread.start()
            return True
    return False

# ============================================================================
# HTML TEMPLATES (inline for simplicity)
# ============================================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Card Tracker - {{ title }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            margin-bottom: 40px;
            padding: 20px 0;
        }

        header h1 {
            font-size: 2.5em;
            color: #00d4ff;
            text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
            margin-bottom: 5px;
        }

        header p {
            color: #888;
            font-size: 0.95em;
        }

        nav {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        nav a {
            display: inline-block;
            padding: 10px 20px;
            background: rgba(0, 212, 255, 0.1);
            color: #00d4ff;
            text-decoration: none;
            border-radius: 5px;
            border: 1px solid #00d4ff;
            transition: all 0.3s ease;
            font-size: 0.9em;
        }

        nav a:hover {
            background: rgba(0, 212, 255, 0.2);
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.2);
        }

        .card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }

        .card h2 {
            color: #00d4ff;
            margin-bottom: 20px;
            font-size: 1.5em;
        }

        .form-group {
            margin-bottom: 15px;
        }

        label {
            display: block;
            margin-bottom: 5px;
            color: #00d4ff;
            font-weight: 500;
            font-size: 0.9em;
        }

        input[type="text"],
        input[type="number"],
        input[type="email"],
        textarea {
            width: 100%;
            padding: 10px 12px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 5px;
            color: #e0e0e0;
            font-size: 0.95em;
            transition: border-color 0.3s ease;
        }

        input[type="text"]:focus,
        input[type="number"]:focus,
        textarea:focus {
            outline: none;
            border-color: #00d4ff;
            box-shadow: 0 0 5px rgba(0, 212, 255, 0.2);
        }

        button {
            background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
            color: #000;
            padding: 12px 25px;
            border: none;
            border-radius: 5px;
            font-weight: 600;
            cursor: pointer;
            font-size: 0.95em;
            transition: all 0.3s ease;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 212, 255, 0.3);
        }

        button:active {
            transform: translateY(0);
        }

        .form-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }

        .results {
            background: rgba(0, 212, 255, 0.05);
            border-left: 4px solid #00d4ff;
            padding: 20px;
            border-radius: 5px;
            margin-top: 20px;
        }

        .stat-box {
            display: inline-block;
            margin-right: 25px;
            margin-bottom: 15px;
        }

        .stat-label {
            color: #888;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .stat-value {
            color: #00d4ff;
            font-size: 1.8em;
            font-weight: bold;
            margin-top: 5px;
        }

        .shipping-note {
            color: #ffa500;
            margin-top: 15px;
            padding: 10px;
            background: rgba(255, 165, 0, 0.1);
            border-left: 3px solid #ffa500;
            border-radius: 3px;
            font-size: 0.9em;
        }

        .error {
            background: rgba(255, 100, 100, 0.1);
            border-left: 4px solid #ff6464;
            padding: 15px;
            border-radius: 5px;
            color: #ff9999;
            margin: 20px 0;
        }

        .success {
            background: rgba(100, 200, 100, 0.1);
            border-left: 4px solid #64c864;
            padding: 15px;
            border-radius: 5px;
            color: #99ff99;
            margin: 20px 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }

        table th {
            background: rgba(0, 212, 255, 0.1);
            padding: 12px;
            text-align: left;
            color: #00d4ff;
            border-bottom: 2px solid rgba(0, 212, 255, 0.3);
            font-weight: 600;
            font-size: 0.9em;
        }

        table td {
            padding: 12px;
            border-bottom: 1px solid rgba(0, 212, 255, 0.1);
        }

        table tr:hover {
            background: rgba(0, 212, 255, 0.05);
        }

        .grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ Card Tracker</h1>
            <p>NFL Football Card Pricing Tool for eBay.ca</p>
        </header>

        <nav>
            <a href="/">Home</a>
            <a href="/#pricing-tool">Price a Card</a>
            <a href="/watchlist">Watchlist</a>
        </nav>

        {{ page_content }}

        <footer>
            <p>Card Tracker © 2026 • Your eBay Card Store Companion</p>
        </footer>
    </div>
</body>
</html>
"""

HOME_TEMPLATE = """
<div class="grid-2">
    <div class="card">
        <h2>📊 Pricing Tool</h2>
        <p style="color: #888; margin-bottom: 20px;">Get real-time market prices for your cards based on eBay.ca data.</p>

        <form method="POST" action="/price">
            <div class="form-row">
                <div class="form-group">
                    <label for="year">Year</label>
                    <input type="text" id="year" name="year" placeholder="e.g., 2024" required>
                </div>
                <div class="form-group">
                    <label for="brand">Brand</label>
                    <input type="text" id="brand" name="brand" placeholder="e.g., Prizm" required>
                </div>
                <div class="form-group">
                    <label for="player">Player Name</label>
                    <input type="text" id="player" name="player" placeholder="e.g., Travis Hunter" required>
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label for="parallel">Parallel</label>
                    <input type="text" id="parallel" name="parallel" placeholder="e.g., Silver, Gold, Base">
                </div>
                <div class="form-group">
                    <label for="card_number">Card # (Optional)</label>
                    <input type="text" id="card_number" name="card_number" placeholder="e.g., 101, RC-1">
                </div>
                <div class="form-group">
                    <label for="insert">Insert/Subset (Optional)</label>
                    <input type="text" id="insert" name="insert" placeholder="e.g., Color Blast, Rookie">
                </div>
            </div>

            <button type="submit">🔍 Get Price Suggestion</button>
        </form>

        {% if result %}
        <div class="results">
            <h3 style="color: #00d4ff; margin-bottom: 20px;">Pricing Analysis for {{ result.player }}</h3>

            <div>
                <div class="stat-box">
                    <div class="stat-label">Quick Sale Price (25th %ile)</div>
                    <div class="stat-value">${{ "%.2f"|format(result.low_price) }} <span style="font-size: 0.5em; color: #888;">CAD</span></div>
                </div>

                <div class="stat-box">
                    <div class="stat-label">Market Price (Median)</div>
                    <div class="stat-value">${{ "%.2f"|format(result.market_price) }} <span style="font-size: 0.5em; color: #888;">CAD</span></div>
                </div>

                <div class="stat-box">
                    <div class="stat-label">Suggested List Price</div>
                    <div class="stat-value" style="color: #00ff99;">${{ "%.2f"|format(result.suggested_price) }} <span style="font-size: 0.5em; color: #888;">CAD</span></div>
                </div>
            </div>

            <div class="shipping-note">
                📦 {{ result.shipping_note }}
            </div>

            <div style="margin-top: 20px; color: #999; font-size: 0.85em;">
                <p>Based on {{ result.num_listings }} active listing(s) on eBay.ca.
                {% if result.num_listings < 5 %}<br><strong style="color: #ffa500;">⚠ Low data — prices may be less reliable with fewer than 5 listings.</strong>{% endif %}</p>
                <p style="margin-top: 5px;">Search query: <code style="background: rgba(0,0,0,0.3); padding: 2px 5px;">{{ result.query }}</code></p>
                <p style="margin-top: 8px; font-style: italic;">💡 Prices are based on current active listings. Cards typically sell for 10-30% below asking price.</p>
            </div>
        </div>
        {% endif %}

        {% if error %}
        <div class="error">
            ❌ {{ error }}
        </div>
        {% endif %}
    </div>

    <div class="card">
        <h2>📈 Market Monitor</h2>
        <p style="color: #888; margin-bottom: 20px;">Latest price data from your watchlist.</p>

        {% if refreshing %}
        <div style="background: rgba(0, 212, 255, 0.1); border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 5px; padding: 12px; margin-bottom: 15px; text-align: center;">
            <span style="color: #00d4ff;">Refreshing prices from eBay... reload in a minute to see updated data.</span>
        </div>
        {% endif %}

        {% if monitor_data %}
        <table>
            <thead>
                <tr>
                    <th>Player</th>
                    <th>Avg Price</th>
                    <th>Trend</th>
                </tr>
            </thead>
            <tbody>
                {% for item in monitor_data[:5] %}
                <tr>
                    <td>{{ item.player }}</td>
                    <td>${{ "%.2f"|format(item.avg_price) }}</td>
                    <td style="color: {% if item.trend and item.trend > 0 %}#00ff99{% elif item.trend and item.trend < 0 %}#ff6464{% else %}#888{% endif %};">
                        {% if item.trend %}{{ "%+.1f"|format(item.trend) }}%{% else %}—{% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
            <a href="/watchlist" style="color: #00d4ff;">View full watchlist →</a>
            <a href="/refresh" style="color: #888; font-size: 0.85em; text-decoration: none;">↻ Refresh prices</a>
        </div>
        {% if last_updated %}
        <p style="color: #555; font-size: 0.75em; text-align: right; margin-top: 5px;">Last updated: {{ last_updated }}</p>
        {% endif %}
        {% else %}
        <p style="color: #666; text-align: center; margin: 30px 0;">
            {% if refreshing %}
            Fetching prices for the first time... reload in a minute.
            {% else %}
            No data yet.
            <a href="/refresh" style="color: #00d4ff;">Fetch prices now →</a>
            {% endif %}<br>
            <a href="/watchlist" style="color: #00d4ff;">View watchlist →</a>
        </p>
        {% endif %}
    </div>
</div>
"""

WATCHLIST_TEMPLATE = """
<div class="card">
    <h2>📋 Watchlist</h2>
    <p style="color: #888; margin-bottom: 20px;">Players you're monitoring for price trends. Run <code style="background: rgba(0,0,0,0.3); padding: 2px 5px;">python main.py</code> daily to fetch new data.</p>

    {% if watchlist %}
    <table>
        <thead>
            <tr>
                <th>Player</th>
                <th>Search Query</th>
                <th>Avg Price</th>
                <th>7-Day Trend</th>
                <th>Data Points</th>
                <th>History</th>
            </tr>
        </thead>
        <tbody>
            {% for item in watchlist %}
            <tr>
                <td><strong>{{ item.player }}</strong><br><span style="color: #666; font-size: 0.8em;">{{ item.notes }}</span></td>
                <td style="font-size: 0.85em;">{{ item.query }}</td>
                <td>{% if item.avg_price %}${{ "%.2f"|format(item.avg_price) }} <span style="color: #666; font-size: 0.75em;">CAD</span>{% else %}—{% endif %}</td>
                <td style="color: {% if item.trend and item.trend > 0 %}#00ff99{% elif item.trend and item.trend < 0 %}#ff6464{% else %}#888{% endif %};">
                    {% if item.trend %}
                        {% if item.trend > 0 %}↑{% elif item.trend < 0 %}↓{% endif %} {{ "%+.1f"|format(item.trend) }}%
                    {% else %}—{% endif %}
                </td>
                <td style="text-align: center;">{{ item.data_points }}</td>
                <td>
                    {% if item.data_points > 0 %}
                    <a href="/history/{{ item.player }}" style="color: #00d4ff; text-decoration: none;">View →</a>
                    {% else %}—{% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p style="color: #666; text-align: center; margin: 40px 0;">
        No players on your watchlist.<br>
        Edit <code style="background: rgba(0,0,0,0.3); padding: 2px 5px;">watchlist.json</code> to add players.
    </p>
    {% endif %}
</div>
"""

HISTORY_TEMPLATE = """
<div class="card">
    <h2>📉 Price History: {{ player }}</h2>
    <p style="color: #888; margin-bottom: 20px;">Price movements over the past 30 days.</p>

    {% if snapshots %}
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Avg Price</th>
                <th>Median</th>
                <th>Range</th>
                <th>Listings</th>
            </tr>
        </thead>
        <tbody>
            {% for snap in snapshots %}
            <tr>
                <td>{{ snap.fetched_at[:10] }}</td>
                <td>${{ "%.2f"|format(snap.avg_price) }}</td>
                <td>${{ "%.2f"|format(snap.median_price) }}</td>
                <td>${{ "%.2f"|format(snap.min_price) }} - ${{ "%.2f"|format(snap.max_price) }}</td>
                <td>{{ snap.num_listings }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p style="color: #666; text-align: center; margin: 40px 0;">
        No price history yet for {{ player }}.<br>
        Run <code style="background: rgba(0,0,0,0.3); padding: 2px 5px;">python main.py</code> to start tracking.
    </p>
    {% endif %}

    <div style="text-align: center; margin-top: 20px;">
        <a href="/watchlist" style="color: #00d4ff; text-decoration: none;">← Back to Watchlist</a>
    </div>
</div>
"""

# ============================================================================
# ROUTES
# ============================================================================


@app.route("/")
def home():
    """Home page with pricing tool and market monitor."""
    # Auto-refresh if data is stale (>24 hours old)
    refreshing = _auto_refresh_if_stale()

    # Get latest monitoring data for the Market Monitor panel
    last_updated = None
    try:
        init_db()
        snapshots = get_latest_snapshots()
        monitor_data = []
        for snap in snapshots:
            trend_info = detect_trends(snap["player"])
            monitor_data.append({
                "player": snap["player"],
                "avg_price": snap["avg_price"],
                "trend": trend_info["percent_change"] if trend_info else None,
            })
        if snapshots:
            latest_time = max(s["fetched_at"] for s in snapshots)
            last_updated = latest_time[:16].replace("T", " ")
    except Exception:
        monitor_data = []

    page = render_template_string(HOME_TEMPLATE, result=None, error=None,
                                  monitor_data=monitor_data, refreshing=refreshing,
                                  last_updated=last_updated)
    return render_template_string(BASE_TEMPLATE, title="Home", page_content=Markup(page))


@app.route("/refresh")
def refresh():
    """Manually trigger a price refresh for all watchlist players."""
    global _refresh_in_progress, _last_refresh_check

    with _refresh_lock:
        if not _refresh_in_progress:
            _refresh_in_progress = True
            _last_refresh_check = datetime.now()
            thread = threading.Thread(target=_refresh_watchlist_data, daemon=True)
            thread.start()

    return redirect(url_for("home"))


@app.route("/price", methods=["POST"])
def price():
    """Calculate and return price suggestion."""
    try:
        year = request.form.get("year", "").strip()
        brand = request.form.get("brand", "").strip()
        player = request.form.get("player", "").strip()
        parallel = request.form.get("parallel", "").strip() or None
        card_number = request.form.get("card_number", "").strip() or None
        insert = request.form.get("insert", "").strip() or None

        # Validate inputs
        if not all([year, brand, player]):
            error = "Year, Brand, and Player are required."
            page = render_template_string(HOME_TEMPLATE, result=None, error=error, monitor_data=[])
            return render_template_string(BASE_TEMPLATE, title="Home", page_content=Markup(page)), 400

        # Get pricing suggestion
        result = suggest_price(year, brand, player, parallel, card_number, insert)

        # If no data found
        if result["num_listings"] == 0:
            error = f"No listings found for '{result['query']}'. Try different search terms."
            page = render_template_string(HOME_TEMPLATE, result=None, error=error, monitor_data=[])
            return render_template_string(BASE_TEMPLATE, title="Home", page_content=Markup(page)), 404

        page = render_template_string(HOME_TEMPLATE, result=result, error=None, monitor_data=[])
        return render_template_string(BASE_TEMPLATE, title="Home", page_content=Markup(page))

    except Exception as e:
        error = f"Error calculating price: {str(e)}"
        page = render_template_string(HOME_TEMPLATE, result=None, error=error, monitor_data=[])
        return render_template_string(BASE_TEMPLATE, title="Home", page_content=Markup(page)), 500


@app.route("/watchlist")
def watchlist():
    """Show watchlist with trend data from database."""
    # Load watchlist.json for player names and queries
    watchlist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")
    try:
        with open(watchlist_path, "r") as f:
            raw_watchlist = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        raw_watchlist = []

    # Enrich with database data
    init_db()
    watchlist_data = []
    for entry in raw_watchlist:
        player = entry["player"]
        snapshots = get_snapshots(player, days=30)
        trend_info = detect_trends(player)

        watchlist_data.append({
            "player": player,
            "query": entry.get("query", ""),
            "notes": entry.get("notes", ""),
            "avg_price": snapshots[0]["avg_price"] if snapshots else None,
            "trend": trend_info["percent_change"] if trend_info else None,
            "data_points": len(snapshots),
        })

    page = render_template_string(WATCHLIST_TEMPLATE, watchlist=watchlist_data)
    return render_template_string(BASE_TEMPLATE, title="Watchlist", page_content=Markup(page))


@app.route("/history/<player>")
def history(player):
    """Show price history for a player from the database."""
    init_db()
    snapshots = get_snapshots(player, days=90)
    page = render_template_string(HISTORY_TEMPLATE, player=player, snapshots=snapshots)
    return render_template_string(BASE_TEMPLATE, title=f"History - {player}", page_content=Markup(page))


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Card Tracker — Flask Web App")
    print("=" * 70)
    print("\n🚀 Starting server...")
    print("📍 Visit: http://localhost:5050")
    print("\nPress Ctrl+C to stop.\n")

    app.run(debug=False, host="0.0.0.0", port=5050)
