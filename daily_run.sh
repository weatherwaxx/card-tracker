#!/bin/bash
# Card Tracker — Daily Run
# Fetches eBay prices, then syncs database to PythonAnywhere.
# Called by launchd at 8am daily.

cd "/Users/catkiinson/Documents/Claude/Projects/Card Tracker"
source venv/bin/activate

echo "=== Fetching eBay prices ==="
python main.py

echo "=== Syncing to cloud ==="
python sync_to_cloud.py
