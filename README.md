# Card Pulse 🏈

A local price tracker for NFL football cards — like a stock tracker for your card inventory. Monitors eBay sold listing data to track trends and alert you to big price moves.

## Quick Start

### 1. Install dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Configure your eBay App ID
Open `config.py` and replace `YOUR_EBAY_APP_ID_HERE` with your Production App ID from [developer.ebay.com](https://developer.ebay.com/my/keys).

### 3. (Optional) Set up email alerts
In `config.py`, fill in your Gmail address and App Password:
- Go to [myaccount.google.com](https://myaccount.google.com) → Security → App Passwords
- Generate a password for "Mail"
- Paste it into `GMAIL_APP_PASSWORD`

### 4. Customize your watchlist
Edit `watchlist.json` to add the players you want to track.

### 5. First run
```bash
python3 main.py
```

### 6. Launch the dashboard
```bash
streamlit run dashboard.py
```
Opens at [localhost:8501](http://localhost:8501).

## Daily Auto-Run (Mac)

To run Card Pulse automatically every day at 8am, create a launchd plist:

Save this as `~/Library/LaunchAgents/com.cardpulse.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cardpulse.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>FULL_PATH_TO/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>FULL_PATH_TO_CARD_PULSE_FOLDER</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>FULL_PATH_TO/card_pulse.log</string>
    <key>StandardErrorPath</key>
    <string>FULL_PATH_TO/card_pulse_error.log</string>
</dict>
</plist>
```

Then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.cardpulse.daily.plist
```

## File Overview

| File | Purpose |
|------|---------|
| `main.py` | Daily runner — fetches prices, detects trends, sends alerts |
| `dashboard.py` | Streamlit web dashboard with charts and watchlist manager |
| `ebay_fetcher.py` | eBay Finding API integration for sold listing prices |
| `trend_detector.py` | 7-day trend calculation, 20%+ move alert logic |
| `notifier.py` | Desktop notifications (Mac/Windows) and Gmail email alerts |
| `database.py` | SQLite database for price history |
| `config.py` | API keys and settings |
| `watchlist.json` | Players to track with eBay search queries |

## Tech Stack

- **Python 3** with SQLite
- **Streamlit** for the dashboard
- **eBay Finding API** (Production) for sold listing data
- **Gmail SMTP** for email alerts (optional)
- **Mac/Windows** desktop notifications
