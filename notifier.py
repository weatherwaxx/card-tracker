"""
Card Pulse — Notifier
======================
Sends Mac/Windows desktop notifications and Gmail email summaries.
Auto-detects OS for the right notification method.
"""

import platform
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, ALERT_EMAIL_TO


def send_desktop_notification(title, message):
    """Send a desktop notification (Mac or Windows)."""
    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            subprocess.run([
                "osascript", "-e",
                f'display notification "{message}" with title "{title}"'
            ], check=True)
            print(f"  Mac notification sent: {title}")

        elif system == "Windows":
            # Windows 10+ toast notification via PowerShell
            powershell_cmd = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName('text')
            $textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode('{message}')) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Card Pulse').Show($toast)
            """
            subprocess.run(["powershell", "-Command", powershell_cmd], check=True)
            print(f"  Windows notification sent: {title}")

        else:
            print(f"  Desktop notifications not supported on {system}")

    except Exception as e:
        print(f"  Notification error: {e}")


def send_email_alert(subject, body):
    """Send an email alert via Gmail SMTP."""
    if GMAIL_ADDRESS == "YOUR_GMAIL_ADDRESS_HERE" or GMAIL_APP_PASSWORD == "YOUR_GMAIL_APP_PASSWORD_HERE":
        print("  Email not configured — skipping email alert.")
        print("  (Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in config.py to enable)")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = ALERT_EMAIL_TO
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        print(f"  Email sent to {ALERT_EMAIL_TO}")
        return True

    except Exception as e:
        print(f"  Email error: {e}")
        return False


def send_alerts(alerts):
    """Send desktop + email notifications for all triggered alerts."""
    if not alerts:
        print("No alerts to send.")
        return

    for alert in alerts:
        direction = "UP" if alert["direction"] == "up" else "DOWN"
        title = f"Card Pulse Alert: {alert['player']}"
        message = (
            f"{alert['player']} is {direction} {abs(alert['percent_change']):.1f}% "
            f"(${alert['current_avg']:.2f} vs ${alert['historical_avg']:.2f} 7-day avg)"
        )

        # Desktop notification
        send_desktop_notification(title, message)

    # Consolidated email with all alerts
    if len(alerts) > 0:
        subject = f"Card Pulse: {len(alerts)} Price Alert(s)"
        body = "Card Pulse Price Alerts\n" + "=" * 40 + "\n\n"
        for alert in alerts:
            direction = "UP" if alert["direction"] == "up" else "DOWN"
            body += (
                f"  {alert['player']}: {direction} {abs(alert['percent_change']):.1f}%\n"
                f"    Current avg: ${alert['current_avg']:.2f}\n"
                f"    7-day avg:   ${alert['historical_avg']:.2f}\n"
                f"    Data points: {alert['num_data_points']}\n\n"
            )
        send_email_alert(subject, body)
