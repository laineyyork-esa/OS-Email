import smtplib
import json
import os
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")
RECIPIENT = "lainey.york@esa.edu.au"

DATA_FILE = "data/os_versions.json"
DAYS_TO_KEEP = 7

TODAY = datetime.now().strftime("%Y-%m-%d")

# -----------------------------------------
# SCRAPERS (simplified examples)
# -----------------------------------------

def scrape_apple_versions():
    """Scrape macOS and iPadOS versions from Apple developer releases page"""
    url = "https://developer.apple.com/news/releases/"
    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    releases = soup.find_all("li", class_="article")
    macos = {"stable": None, "beta": None, "release_date": None}
    ipados = {"stable": None, "beta": None, "release_date": None}
    for r in releases:
        text = r.get_text(" ", strip=True)
        if "macOS" in text and "beta" not in text.lower():
            macos["stable"] = text.split(" ")[1]
            macos["release_date"] = TODAY
        elif "macOS" in text and "beta" in text.lower():
            macos["beta"] = text.split(" ")[1]
            macos["release_date"] = TODAY
        elif "iPadOS" in text and "beta" not in text.lower():
            ipados["stable"] = text.split(" ")[1]
            ipados["release_date"] = TODAY
        elif "iPadOS" in text and "beta" in text.lower():
            ipados["beta"] = text.split(" ")[1]
            ipados["release_date"] = TODAY
    return {"macOS": macos, "iPadOS": ipados}


def scrape_chrome_versions():
    """Scrape Chrome stable/beta versions from developer page"""
    url = "https://developer.chrome.com/release-notes"
    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    versions = {"stable": None, "beta": None, "release_date": TODAY}
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True)
        if "Stable" in text:
            versions["stable"] = text.split(" ")[1]
        elif "Beta" in text:
            versions["beta"] = text.split(" ")[1]
    return {"ChromeOS": versions}


def scrape_windows_versions():
    """Scrape Windows release health info"""
    url = "https://learn.microsoft.com/en-us/windows/release-health/"
    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    versions = {"stable": None, "beta": None, "release_date": TODAY}
    for h3 in soup.find_all("h3"):
        text = h3.get_text(strip=True)
        if "Windows 11" in text:
            versions["stable"] = "11"
        elif "Insider" in text:
            versions["beta"] = text
    return {"Windows": versions}


def scrape_all():
    data = {}
    data.update(scrape_apple_versions())
    data.update(scrape_chrome_versions())
    data.update(scrape_windows_versions())
    return data


# -----------------------------------------
# DATA HANDLING
# -----------------------------------------

def load_history():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_history(history):
    # trim to 7 days
    keys = sorted(history.keys())[-DAYS_TO_KEEP:]
    trimmed = {k: history[k] for k in keys}
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)


def detect_changes(prev_data, curr_data):
    changes = []
    for os_name, curr in curr_data.items():
        prev = prev_data.get(os_name, {})
        if curr != prev:
            if not prev:
                changes.append(f"🟢 New platform detected: {os_name}")
            else:
                for field in ["stable", "beta", "release_date"]:
                    if curr.get(field) != prev.get(field):
                        changes.append(f"🟨 {os_name} {field} changed from {prev.get(field)} → {curr.get(field)}")
    for os_name in prev_data:
        if os_name not in curr_data:
            changes.append(f"🟥 {os_name} removed from latest data")
    return changes


# -----------------------------------------
# EMAIL
# -----------------------------------------

def build_email(changes, curr_data):
    summary = "<br>".join(changes) if changes else "No changes detected in the last 24 hours."

    html_table = """
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
        <tr><th>Platform</th><th>Stable</th><th>Beta</th><th>Release Date</th></tr>
    """
    for os_name, v in curr_data.items():
        html_table += f"<tr><td>{os_name}</td><td>{v.get('stable','-')}</td><td>{v.get('beta','-')}</td><td>{v.get('release_date','-')}</td></tr>"
    html_table += "</table>"

    html_body = f"""
    <p>{summary}</p>
    {html_table}
    """

    text_body = summary + "\n\n" + "\n".join(
        [f"{os_name}: {v.get('stable','-')} | {v.get('beta','-')} | {v.get('release_date','-')}" for os_name, v in curr_data.items()]
    )

    return html_body, text_body


def send_email(html_body, text_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📱 Daily OS Version Report — {TODAY}"
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
        print("✅ Email sent successfully")


# -----------------------------------------
# MAIN
# -----------------------------------------

def main():
    curr_data = scrape_all()
    history = load_history()
    prev_data = history.get(sorted(history.keys())[-1], {}) if history else {}
    changes = detect_changes(prev_data, curr_data)
    html_body, text_body = build_email(changes, curr_data)
    send_email(html_body, text_body)
    history[TODAY] = curr_data
    save_history(history)


if __name__ == "__main__":
    main()
