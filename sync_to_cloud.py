"""
Card Tracker — Cloud Sync
===========================
Uploads the local database to PythonAnywhere and reloads the web app.
Run after main.py to keep the cloud dashboard at cardllama.pythonanywhere.com up to date.
"""

import os
import requests

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(PROJECT_DIR, "pythonanywhere_token.txt")
DB_FILE = os.path.join(PROJECT_DIR, "card_pulse.db")

PA_USER = "cardllama"
PA_API_BASE = f"https://www.pythonanywhere.com/api/v0/user/{PA_USER}"


def get_token():
    with open(TOKEN_FILE, "r") as f:
        return f.read().strip()


def upload_database(token):
    """Upload card_pulse.db to PythonAnywhere."""
    url = f"{PA_API_BASE}/files/path/home/{PA_USER}/card-tracker/card_pulse.db"
    headers = {"Authorization": f"Token {token}"}

    with open(DB_FILE, "rb") as f:
        response = requests.post(url, headers=headers, files={"content": f})

    if response.status_code in (200, 201):
        print(f"  Database uploaded successfully ({response.status_code})")
        return True
    else:
        print(f"  Upload failed: {response.status_code} - {response.text}")
        return False


def reload_webapp(token):
    """Reload the PythonAnywhere web app."""
    url = f"{PA_API_BASE}/webapps/{PA_USER}.pythonanywhere.com/reload/"
    headers = {"Authorization": f"Token {token}"}

    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        print(f"  Web app reloaded successfully")
        return True
    else:
        print(f"  Reload failed: {response.status_code} - {response.text}")
        return False


def run():
    print("\nSyncing to PythonAnywhere...")

    if not os.path.exists(TOKEN_FILE):
        print("  No token file found — skipping cloud sync.")
        return

    if not os.path.exists(DB_FILE):
        print("  No database file found — skipping cloud sync.")
        return

    token = get_token()
    if upload_database(token):
        reload_webapp(token)

    print("Cloud sync complete.\n")


if __name__ == "__main__":
    run()
