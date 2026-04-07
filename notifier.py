"""
Card Tracker — Notifier
========================
Sends Mac desktop notifications and a daily Gmail digest email.
Digest includes price spikes, price drops, and low-inventory alerts.
"""

import platform
import subprocess
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, ALERT_EMAIL_TO, ALERT_THRESHOLD_PERCENT, LOW_INVENTORY_THRESHOLD


def send_desktop_notification(title, message):
    """Send a macOS desktop notification."""
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"'
        ], check=True)
        print(f"  Mac notification sent: {title}")
    except Exception as e:
        print(f"  Notification error: {e}")


def send_email_alert(subject, body_html):
    """Send an HTML email via Gmail SMTP."""
    if GMAIL_APP_PASSWORD == "YOUR_GMAIL_APP_PASSWORD_HERE":
        print("  Email not configured — skipping email alert.")
        print("  (Set GMAIL_APP_PASSWORD in config.py to enable)")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = ALERT_EMAIL_TO
        msg["Subject"] = subject

        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        print(f"  Email sent to {ALERT_EMAIL_TO}")
        return True

    except Exception as e:
        print(f"  Email error: {e}")
        return False


def _format_digest_html(digest):
    """Build an HTML email body for the daily digest."""
    date_str = datetime.now().strftime("%B %d, %Y")
    total = digest["total_alerts"]

    html = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #1a1a2e; color: #e0e0e0; padding: 20px;">
        <div style="background: #16213e; border-radius: 12px; padding: 24px; border: 1px solid #0f3460;">
            <h1 style="color: #00d4ff; margin: 0 0 4px 0; font-size: 22px;">Card Tracker Daily Digest</h1>
            <p style="color: #888; margin: 0 0 20px 0; font-size: 14px;">{date_str}</p>
    """

    if total == 0:
        html += """
            <div style="background: #1a1a2e; border-radius: 8px; padding: 16px; text-align: center;">
                <p style="color: #888; margin: 0;">No significant price movements or inventory alerts today. All quiet.</p>
            </div>
        """
    else:
        # Price Spikes
        if digest["spikes"]:
            html += f"""
            <div style="margin-bottom: 20px;">
                <h2 style="color: #4ade80; font-size: 16px; margin: 0 0 12px 0;">📈 Price Spikes ({len(digest['spikes'])})</h2>
            """
            for s in digest["spikes"]:
                html += f"""
                <div style="background: #1a2e1a; border-left: 3px solid #4ade80; border-radius: 4px; padding: 12px; margin-bottom: 8px;">
                    <strong style="color: #4ade80;">{s['player']}</strong>
                    <span style="color: #4ade80; float: right;">+{s['percent_change']:.1f}%</span><br>
                    <span style="color: #aaa; font-size: 13px;">${s['current_avg']:.2f} CAD (was ${s['historical_avg']:.2f} 7-day avg)</span>
                </div>
                """
            html += "</div>"

        # Price Drops
        if digest["drops"]:
            html += f"""
            <div style="margin-bottom: 20px;">
                <h2 style="color: #f87171; font-size: 16px; margin: 0 0 12px 0;">📉 Price Drops ({len(digest['drops'])})</h2>
            """
            for d in digest["drops"]:
                html += f"""
                <div style="background: #2e1a1a; border-left: 3px solid #f87171; border-radius: 4px; padding: 12px; margin-bottom: 8px;">
                    <strong style="color: #f87171;">{d['player']}</strong>
                    <span style="color: #f87171; float: right;">{d['percent_change']:.1f}%</span><br>
                    <span style="color: #aaa; font-size: 13px;">${d['current_avg']:.2f} CAD (was ${d['historical_avg']:.2f} 7-day avg)</span>
                </div>
                """
            html += "</div>"

        # Low Inventory
        if digest["low_inventory"]:
            html += f"""
            <div style="margin-bottom: 20px;">
                <h2 style="color: #fbbf24; font-size: 16px; margin: 0 0 12px 0;">⚠️ Low Inventory ({len(digest['low_inventory'])})</h2>
            """
            for li in digest["low_inventory"]:
                prev_note = ""
                if li["previous_avg_listings"] is not None:
                    prev_note = f" (was ~{li['previous_avg_listings']} avg)"
                html += f"""
                <div style="background: #2e2a1a; border-left: 3px solid #fbbf24; border-radius: 4px; padding: 12px; margin-bottom: 8px;">
                    <strong style="color: #fbbf24;">{li['player']}</strong>
                    <span style="color: #fbbf24; float: right;">Only {li['current_listings']} listings</span><br>
                    <span style="color: #aaa; font-size: 13px;">Avg price: ${li['current_avg_price']:.2f} CAD{prev_note} — potential scarcity, good time to list</span>
                </div>
                """
            html += "</div>"

    # Market overview of all tracked players
    if digest["all_trends"]:
        html += """
        <div style="margin-top: 20px; border-top: 1px solid #333; padding-top: 16px;">
            <h2 style="color: #00d4ff; font-size: 16px; margin: 0 0 12px 0;">Full Watchlist</h2>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <tr style="color: #888; text-align: left;">
                    <th style="padding: 6px 8px;">Player</th>
                    <th style="padding: 6px 8px; text-align: right;">Avg Price</th>
                    <th style="padding: 6px 8px; text-align: right;">7-Day Avg</th>
                    <th style="padding: 6px 8px; text-align: right;">Change</th>
                </tr>
        """
        for t in sorted(digest["all_trends"], key=lambda x: abs(x["percent_change"]), reverse=True):
            if t["percent_change"] > 0:
                color = "#4ade80"
                arrow = "↑"
            elif t["percent_change"] < 0:
                color = "#f87171"
                arrow = "↓"
            else:
                color = "#888"
                arrow = "→"

            html += f"""
                <tr style="border-top: 1px solid #2a2a3e;">
                    <td style="padding: 6px 8px; color: #e0e0e0;">{t['player']}</td>
                    <td style="padding: 6px 8px; text-align: right; color: #e0e0e0;">${t['current_avg']:.2f}</td>
                    <td style="padding: 6px 8px; text-align: right; color: #888;">${t['historical_avg']:.2f}</td>
                    <td style="padding: 6px 8px; text-align: right; color: {color};">{arrow} {t['percent_change']:+.1f}%</td>
                </tr>
            """
        html += "</table></div>"

    html += f"""
            <p style="color: #555; font-size: 12px; margin-top: 20px; text-align: center;">
                Card Tracker — Alerts: ≥{ALERT_THRESHOLD_PERCENT}% price move | &lt;{LOW_INVENTORY_THRESHOLD} listings<br>
                View dashboard: <a href="http://localhost:5050" style="color: #00d4ff;">http://localhost:5050</a>
            </p>
        </div>
    </body>
    </html>
    """

    return html


def send_daily_digest(digest):
    """Send the daily digest as a desktop notification + email."""
    total = digest["total_alerts"]
    date_str = datetime.now().strftime("%b %d")

    # Desktop notification summary
    if total > 0:
        parts = []
        if digest["spikes"]:
            parts.append(f"{len(digest['spikes'])} spike(s)")
        if digest["drops"]:
            parts.append(f"{len(digest['drops'])} drop(s)")
        if digest["low_inventory"]:
            parts.append(f"{len(digest['low_inventory'])} low inventory")
        summary = ", ".join(parts)
        send_desktop_notification("Card Tracker", f"{total} alert(s): {summary}")
    else:
        send_desktop_notification("Card Tracker", "Daily digest sent — no alerts today.")

    # Email digest
    if total > 0:
        subject = f"Card Tracker: {total} alert(s) — {date_str}"
    else:
        subject = f"Card Tracker: All quiet — {date_str}"

    html = _format_digest_html(digest)
    send_email_alert(subject, html)


# Legacy function for backward compatibility
def send_alerts(alerts):
    """Send desktop + email notifications for triggered price alerts."""
    if not alerts:
        print("No alerts to send.")
        return

    for alert in alerts:
        direction = "UP" if alert["direction"] == "up" else "DOWN"
        title = f"Card Tracker: {alert['player']}"
        message = (
            f"{alert['player']} is {direction} {abs(alert['percent_change']):.1f}% "
            f"(${alert['current_avg']:.2f} vs ${alert['historical_avg']:.2f} 7-day avg)"
        )
        send_desktop_notification(title, message)
