import requests
from bs4 import BeautifulSoup
import dateparser
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os

# -------- CONFIG --------
EMAIL_FROM = os.environ.get("EMAIL_FROM")          # e.g., laineyyork97@gmail.com
EMAIL_TO = os.environ.get("EMAIL_TO")              # e.g., lainey.york@esa.edu.au
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")    # Gmail App Password
HISTORY_FILE = "data/os_versions.json"
OS_LIST = ["macOS", "iPadOS", "Windows", "ChromeOS"]
RSS_URL = "https://developer.apple.com/news/rss/news.rss"
WINDOWS_URL = "https://learn.microsoft.com/en-us/windows/release-health/"
CHROMEDASH_URL = "https://chromiumdash.appspot.com/schedule"

# Ensure data folder exists
os.makedirs("data", exist_ok=True)

# -------- SCRAPERS --------

def scrape_apple_versions():
    versions = {"macOS": {}, "iPadOS": {}}
    try:
        r = requests.get(RSS_URL)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml-xml")
        items = soup.find_all("item")

        for item in items:
            title = item.title.text
            pub_date = item.pubDate.text
            parsed_date = dateparser.parse(pub_date).strftime("%d %b %Y")

            if "macOS" in title:
                versions["macOS"]["beta"] = title
                versions["macOS"]["beta_release_date"] = parsed_date
            elif "iPadOS" in title:
                versions["iPadOS"]["beta"] = title
                versions["iPadOS"]["beta_release_date"] = parsed_date

        # Example stable versions (replace with actual logic if scraping is available)
        versions["macOS"]["stable"] = "26.1"
        versions["iPadOS"]["stable"] = "26.0.1"

    except Exception as e:
        print(f"Apple scrape error: {e}")
        for os_name in ["macOS", "iPadOS"]:
            versions[os_name] = {"stable": "-", "beta": "-", "beta_release_date": "-"}

    return versions

def scrape_windows_versions():
    versions = {"Windows": {}}
    try:
        # Simplified: Windows stable version
        versions["Windows"]["stable"] = "Windows 11 25H5"
        versions["Windows"]["beta"] = "-"
        versions["Windows"]["beta_release_date"] = "-"
    except Exception as e:
        print(f"Windows scrape error: {e}")
        versions["Windows"] = {"stable": "-", "beta": "-", "beta_release_date": "-"}
    return versions

def scrape_chrome_versions():
    versions = {"ChromeOS": {}}
    try:
        r = requests.get(CHROMEDASH_URL)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if cells and "Beta" in cells[0].text:
                    versions["ChromeOS"]["beta"] = cells[0].text.strip()
                    versions["ChromeOS"]["beta_release_date"] = cells[1].text.strip()
                elif cells and "Stable" in cells[0].text:
                    versions["ChromeOS"]["stable"] = cells[0].text.strip()
        if not versions["ChromeOS"]:
            versions["ChromeOS"] = {"stable": "-", "beta": "-", "beta_release_date": "-"}
    except Exception as e:
        print(f"ChromeOS scrape error: {e}")
        versions["ChromeOS"] = {"stable": "-", "beta": "-", "beta_release_date": "-"}
    return versions

# -------- HISTORY & CHANGE DETECTION --------

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def detect_changes(history, data):
    changes = {}
    for os_name in OS_LIST:
        old = history.get(os_name, {})
        new = data.get(os_name, {})
        changes[os_name] = {}
        for key in ["stable", "beta", "beta_release_date"]:
            if old.get(key) != new.get(key):
                changes[os_name][key] = new.get(key, "-")
    return changes

# -------- EMAIL --------

def send_email(data, changes):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = "Daily OS Versions"

    html = "<h3>Daily OS Versions</h3>"

    # Summary
    for os_name in OS_LIST:
        update_text = []
        for key, value in changes.get(os_name, {}).items():
            if value != "-":
                update_text.append(f"{key.capitalize()}: {value}")
        if update_text:
            html += f"<p>🆕 {os_name} update: {' | '.join(update_text)}</p>"

    # Table
    html += "<table border='1' cellpadding='5'><tr><th>Platform</th><th>Stable</th><th>Beta</th><th>Beta Release Date</th></tr>"
    for os_name in OS_LIST:
        html += f"<tr><td>{os_name}</td><td>{data.get(os_name, {}).get('stable', '-')}</td><td>{data.get(os_name, {}).get('beta', '-')}</td><td>{data.get(os_name, {}).get('beta_release_date', '-')}</td></tr>"
    html += "</table>"

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_FROM, SMTP_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully")
    except Exception as e:
        print(f"Email send error: {e}")

# -------- MAIN --------

def main():
    data = {}
    data.update(scrape_apple_versions())
    data.update(scrape_windows_versions())
    data.update(scrape_chrome_versions())

    history = load_history()
    changes = detect_changes(history, data)
    save_history(data)
    send_email(data, changes)

if __name__ == "__main__":
    main()
