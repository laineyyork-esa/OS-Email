import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import dateparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ---------- CONFIG ----------
HISTORY_FILE = "data/os_versions.json"
EMAIL_FROM = "laineyyork97@gmail.com"
EMAIL_TO = "lainey.york@esa.edu.au"
EMAIL_SUBJECT = "Daily OS Versions"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_PASSWORD = "YOUR_APP_PASSWORD_HERE"  # Gmail App Password
OS_LIST = ["macOS", "iPadOS", "Windows", "ChromeOS"]

# ---------- HELPER FUNCTIONS ----------

def ensure_history_file():
    import os
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w") as f:
            json.dump({}, f)

def load_history():
    ensure_history_file()
    with open(HISTORY_FILE) as f:
        return json.load(f)

def save_history(data):
    ensure_history_file()
    # Keep only last 7 days
    today = datetime.now().strftime("%Y-%m-%d")
    history = load_history()
    history[today] = data
    keys = sorted(history.keys(), reverse=True)[:7]
    new_history = {k: history[k] for k in keys}
    with open(HISTORY_FILE, "w") as f:
        json.dump(new_history, f, indent=2)

def detect_changes(old_data, new_data):
    changes = []
    for os_name in OS_LIST:
        old = old_data.get(os_name, {})
        new = new_data.get(os_name, {})
        for field in ["stable", "beta", "beta_release_date"]:
            if old.get(field) != new.get(field):
                changes.append(f"{os_name} {field} changed from {old.get(field, '-') } to {new.get(field, '-')}")
    return changes

# ---------- SCRAPERS ----------

def scrape_apple_versions():
    versions = {}
    try:
        resp = requests.get("https://developer.apple.com/news/rss/news.rss")
        soup = BeautifulSoup(resp.content, "xml")
        items = soup.find_all("item")
        for os_name in ["macOS", "iPadOS"]:
            stable, beta, beta_date = "-", "-", "-"
            for item in items:
                title = item.title.text
                pub_date = item.pubDate.text
                # Parse only numeric version numbers
                import re
                version_match = re.search(rf"{os_name}\s\d+(\.\d+)*", title, re.IGNORECASE)
                beta_match = re.search(rf"{os_name}\s\d+(\.\d+)*\sBeta\s?\d*", title, re.IGNORECASE)
                if beta_match:
                    beta = beta_match.group(0)
                    beta_date = dateparser.parse(pub_date).strftime("%d %b %Y")
                elif version_match and stable == "-":
                    stable = version_match.group(0)
            versions[os_name] = {
                "stable": stable,
                "beta": beta,
                "beta_release_date": beta_date
            }
    except Exception as e:
        print("Apple scrape error:", e)
    return versions

def scrape_windows_versions():
    versions = {}
    try:
        resp = requests.get("https://learn.microsoft.com/en-us/windows/release-health/")
        soup = BeautifulSoup(resp.content, "html.parser")
        # Find the latest Windows 11 version
        table = soup.find("table")
        stable = "-"
        if table:
            for row in table.find_all("tr"):
                cols = row.find_all("td")
                if cols and "Windows 11" in cols[0].text:
                    stable = cols[0].text.strip()
                    break
        versions["Windows"] = {
            "stable": stable,
            "beta": "-",
            "beta_release_date": "-"
        }
    except Exception as e:
        print("Windows scrape error:", e)
    return versions

def scrape_chrome_versions():
    versions = {}
    try:
        resp = requests.get("https://chromiumdash.appspot.com/schedule")
        soup = BeautifulSoup(resp.content, "html.parser")
        # Look for the Beta promotion row for Chrome
        stable, beta, beta_date = "-", "-", "-"
        table = soup.find("table")
        if table:
            for row in table.find_all("tr"):
                cols = row.find_all("td")
                if cols:
                    text = cols[0].text.strip()
                    if "Stable" in text:
                        stable = cols[1].text.strip()
                    if "Beta" in text:
                        beta = cols[1].text.strip()
                        beta_date = cols[2].text.strip()
        versions["ChromeOS"] = {
            "stable": stable,
            "beta": beta,
            "beta_release_date": beta_date
        }
    except Exception as e:
        print("ChromeOS scrape error:", e)
    return versions

# ---------- EMAIL ----------

def send_email(data, changes):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = EMAIL_SUBJECT

    summary = ""
    if changes:
        summary += "🆕 Changes in last 24h:\n"
        for c in changes:
            summary += f"{c}\n"
    summary += "\n"

    table_html = "<table border='1' style='border-collapse: collapse'><tr><th>Platform</th><th>Stable</th><th>Beta</th><th>Beta Release Date</th></tr>"
    for os_name in OS_LIST:
        row = data.get(os_name, {})
        table_html += f"<tr><td>{os_name}</td><td>{row.get('stable', '-')}</td><td>{row.get('beta', '-')}</td><td>{row.get('beta_release_date', '-')}</td></tr>"
    table_html += "</table>"

    msg.attach(MIMEText(summary + table_html, 'html'))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_FROM, SMTP_PASSWORD)
    server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    server.quit()

# ---------- MAIN ----------

def main():
    data = {}
    data.update(scrape_apple_versions())
    data.update(scrape_windows_versions())
    data.update(scrape_chrome_versions())

    history = load_history()
    changes = detect_changes(history.get(list(history.keys())[-1], {}), data) if history else []

    save_history(data)
    send_email(data, changes)

if __name__ == "__main__":
    main()
