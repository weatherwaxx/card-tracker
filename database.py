"""
Card Tracker — Database Module
================================
SQLite database for storing price snapshots and listing data over time.
"""

import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH


def get_connection():
    """Get a connection to the SQLite database."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Daily price snapshots — one row per player per day
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player TEXT NOT NULL,
            avg_price REAL NOT NULL,
            median_price REAL NOT NULL,
            min_price REAL,
            max_price REAL,
            num_listings INTEGER,
            fetched_at TEXT NOT NULL
        )
    """)

    # Individual listing records for reference
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player TEXT NOT NULL,
            title TEXT,
            price REAL NOT NULL,
            listing_date TEXT,
            fetched_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_snapshot(player, avg_price, median_price, min_price, max_price, num_listings):
    """Save a price snapshot for a player."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO price_snapshots
           (player, avg_price, median_price, min_price, max_price, num_listings, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (player, avg_price, median_price, min_price, max_price, num_listings,
         datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def save_listings(player, listings):
    """Save individual listing records."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    for listing in listings:
        cursor.execute(
            """INSERT INTO listings (player, title, price, listing_date, fetched_at)
               VALUES (?, ?, ?, ?, ?)""",
            (player, listing.get("title", ""), listing["price"],
             listing.get("listing_date", ""), now)
        )
    conn.commit()
    conn.close()


def get_snapshots(player, days=30):
    """Get price snapshots for a player over the last N days."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM price_snapshots
           WHERE player = ?
           ORDER BY fetched_at DESC
           LIMIT ?""",
        (player, days)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_latest_snapshots():
    """Get the most recent snapshot for each player."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ps.* FROM price_snapshots ps
        INNER JOIN (
            SELECT player, MAX(fetched_at) as max_date
            FROM price_snapshots
            GROUP BY player
        ) latest ON ps.player = latest.player AND ps.fetched_at = latest.max_date
        ORDER BY ps.player
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_players():
    """Get a list of all tracked players in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT player FROM price_snapshots ORDER BY player")
    players = [row["player"] for row in cursor.fetchall()]
    conn.close()
    return players


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
