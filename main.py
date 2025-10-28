import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# ---------- CONFIG ----------
EMAIL_FROM = os.getenv("GMAIL_USER")
EMAIL_TO = os.getenv("EMAIL_TO")
SMTP_PASSWORD = os.getenv("GMAIL_PASS")
HISTORY_FILE = "data/os_versions.json"
KEEP_DAYS = 7

# ---------- SCRAPE FUNCTIONS ----------
def scrape_apple_releases():
    url = "https://developer.apple.com/news/releases/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    versions = {
        "macOS": {"stable": "-", "beta": "-", "beta_release_date": "-"},
        "iPadOS": {"stable": "-", "beta": "-", "beta_release_date": "-"}
    }

    articles = soup.find_all("article")
    for article in articles:
        header = article.find("h2")
        date_elem = article.find("time")
        if not header or not date_elem:
            continue
        
        title = header.text.strip()
        release_date = parser.parse(date_elem.text.strip()).strftime("%d %b %Y")

        if "macOS" in title:
            if "beta" in title.lower():
                versions["macOS"]["beta"] = title
                versions["macOS"]["beta_release_date"] = release_date
            else:
                versions["macOS"]["stable"] = title
        elif "iPadOS" in title:
            if "beta" in title.lower():
                versions["iPadOS"]["beta"] = title
                versions["iPadOS"]["beta_release_date"] = release_date
            else:
                versions["iPadOS"]["stable"] = title

    return versions


def scrape_windows_versions():
    url = "https://learn.microsoft.com/en-us/windows/release-health/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Example scrape logic
    stable_version = soup.find("span", class_="release-version")
    stable = stable_version.text.strip() if stable_version else "-"

    return {"Windows": {"stable": stable, "beta": "-", "beta_release_date": "-"}}


def scrape_chrome_versions():
    url = "https://chromiumdash.appspot.com/schedule"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    stable = "-"
    beta = "-"
    beta_date = "-"

    table = soup.find("table")
    if table:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                channel = cells[0].text.strip()
                version = cells[1].text.strip()
                date = cells[2].text.strip()
                if channel.lower() == "beta":
                    beta = version
                    beta_date = date
                elif channel.lower() == "stable":
                    stable = version

    return {"ChromeOS": {"stable": stable, "beta": beta, "beta_release_date": beta_date}}

# ---------- HISTORY ----------
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_history(data):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    history[today] = data

    # Keep last 7 days
    keys = sorted(history.keys(), reverse=True)[:KEEP_DAYS]
    history = {k: history[k] for k in keys}

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ---------- CHANGE DETECTION ----------
def detect_changes(history, data):
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    changes = {}
    prev = history.get(yesterday, {})

    for os_name, vals in data.items():
        changes[os_name] = {"stable": "-", "beta": "-", "beta_release_date": "-"}
        for key in vals:
            if prev.get(os_name, {}).get(key) != vals[key]:
                changes[os_name][key] = vals[key]
    return changes

# ---------- EMAIL ----------
def send_email(data, changes):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = f"Daily OS Versions - {datetime.now().strftime('%d %b %Y')}"

    html = f"<h2>Daily OS Versions - {datetime.now().strftime('%d %b %Y')}</h2>"

    # Short summary of changes
    html += "<h3>🆕 Short summary of changes:</h3>"
    for os_name, vals in changes.items():
        html += f"🆕 {os_name} update: Stable: {vals['stable']}, Beta: {vals['beta']}, Beta Release Date: {vals['beta_release_date']}<br>"

    # Table
    html += "<br><table border='1' cellpadding='5'><tr><th>Platform</th><th>Stable</th><th>Beta</th><th>Beta Release Date</th></tr>"
    for os_name, vals in data.items():
        html += f"<tr><td>{os_name}</td><td>{vals['stable']}</td><td>{vals['beta']}</td><td>{vals['beta_release_date']}</td></tr>"
    html += "</table>"

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())


# ---------- MAIN ----------
def main():
    data = {}
    try:
        data.update(scrape_apple_releases())
    except Exception as e:
        print("Apple scrape error:", e)
    try:
        data.update(scrape_windows_versions())
    except Exception as e:
        print("Windows scrape error:", e)
    try:
        data.update(scrape_chrome_versions())
    except Exception as e:
        print("ChromeOS scrape error:", e)

    history = load_history()
    changes = detect_changes(history, data)
    save_history(data)
    send_email(data, changes)


if __name__ == "__main__":
    main()
