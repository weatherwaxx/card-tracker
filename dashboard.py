"""
Card Pulse — Streamlit Dashboard
==================================
Web dashboard showing price history charts and a watchlist manager.
Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from database import init_db, get_snapshots, get_all_players
from trend_detector import detect_trends

# Page config
st.set_page_config(page_title="Card Pulse", page_icon="🏈", layout="wide")

# Initialize database
init_db()

# Title
st.title("🏈 Card Pulse")
st.caption("NFL Football Card Price Tracker")

# Sidebar — Watchlist Manager
st.sidebar.header("Watchlist Manager")

watchlist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")


def load_watchlist():
    with open(watchlist_path, "r") as f:
        return json.load(f)


def save_watchlist(watchlist):
    with open(watchlist_path, "w") as f:
        json.dump(watchlist, f, indent=4)


watchlist = load_watchlist()

# Display current watchlist
st.sidebar.subheader("Current Players")
for i, entry in enumerate(watchlist):
    col1, col2 = st.sidebar.columns([3, 1])
    col1.write(f"**{entry['player']}**")
    if col2.button("Remove", key=f"remove_{i}"):
        watchlist.pop(i)
        save_watchlist(watchlist)
        st.rerun()

# Add new player
st.sidebar.subheader("Add Player")
new_player = st.sidebar.text_input("Player name")
new_query = st.sidebar.text_input("eBay search query", placeholder="e.g., Lamar Jackson football card")
new_notes = st.sidebar.text_input("Notes (optional)")

if st.sidebar.button("Add to Watchlist"):
    if new_player and new_query:
        watchlist.append({
            "player": new_player,
            "query": new_query,
            "notes": new_notes,
        })
        save_watchlist(watchlist)
        st.sidebar.success(f"Added {new_player}!")
        st.rerun()
    else:
        st.sidebar.error("Please enter both a player name and search query.")

# Main content — Price History Charts
st.header("Price History")

players = get_all_players()

if not players:
    st.info(
        "No price data yet! Run `python3 main.py` to fetch your first batch of prices, "
        "then come back here to see charts."
    )
else:
    # Player selector
    selected_player = st.selectbox("Select a player", players)

    if selected_player:
        snapshots = get_snapshots(selected_player, days=90)

        if snapshots:
            # Convert to DataFrame
            df = pd.DataFrame(snapshots)
            df["fetched_at"] = pd.to_datetime(df["fetched_at"])
            df = df.sort_values("fetched_at")

            # Price chart
            st.subheader(f"{selected_player} — Average Sold Price")
            chart_data = df.set_index("fetched_at")[["avg_price", "median_price"]]
            chart_data.columns = ["Average", "Median"]
            st.line_chart(chart_data)

            # Stats summary
            col1, col2, col3, col4 = st.columns(4)
            latest = snapshots[0]
            col1.metric("Current Avg", f"${latest['avg_price']:.2f}")
            col2.metric("Median", f"${latest['median_price']:.2f}")
            col3.metric("Range", f"${latest['min_price']:.2f} - ${latest['max_price']:.2f}")
            col4.metric("Listings", latest["num_listings"])

            # Trend info
            trend = detect_trends(selected_player)
            if trend:
                direction = "📈" if trend["direction"] == "up" else "📉"
                color = "green" if trend["direction"] == "up" else "red"
                st.markdown(
                    f"**7-Day Trend:** {direction} "
                    f"<span style='color:{color}'>{trend['percent_change']:+.1f}%</span> "
                    f"(vs ${trend['historical_avg']:.2f} avg)",
                    unsafe_allow_html=True,
                )
                if trend["alert"]:
                    st.warning(
                        f"Alert: {selected_player} has moved "
                        f"{abs(trend['percent_change']):.1f}% in the last 7 days!"
                    )

            # Raw data table
            with st.expander("View raw data"):
                st.dataframe(df[["fetched_at", "avg_price", "median_price", "min_price", "max_price", "num_listings"]])

# Footer
st.markdown("---")
st.caption("Card Pulse — Built with Streamlit | Data from eBay sold listings")
