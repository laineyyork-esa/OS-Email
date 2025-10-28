import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup
import dateparser

# Paths
HISTORY_FILE = "data/os_versions.json"

# Gmail setup
EMAIL_FROM = os.environ["gmail_user"]
EMAIL_TO = os.environ["gmail_user"]  # change if sending to a different recipient
SMTP_PASSWORD = os.environ["gmail_pass"]

# Initialize OS data
OS_LIST = ["macOS", "iPadOS", "Windows", "ChromeOS"]

def ensure_data_folder():
    if not os.path.exists("data"):
        os.makedirs("data")

def scrape_apple_versions():
    url = "https://developer.apple.com/news/rss/news.rss"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")
        versions = {"macOS": {}, "iPadOS": {}}
        for item in items:
            title = item.title.text
            pub_date = item.pubDate.text
            if "macOS" in title:
                versions["macOS"]["beta"] = title
                versions["macOS"]["beta_release_date"] = dateparser.parse(pub_date).strftime("%d %b %Y")
            elif "iPadOS" in title:
                versions["iPadOS"]["beta"] = title
                versions["iPadOS"]["beta_release_date"] = dateparser.parse(pub_date).strftime("%d %b %Y")
        return versions
    except Exception as e:
        print(f"Apple scrape error: {e}")
        return {}

def scrape_windows_versions():
    try:
        url = "https://learn.microsoft.com/en-us/windows/release-health/"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        stable = soup.find("td", string=lambda x: "Windows 11" in x if x else False)
        stable_version = stable.text.strip() if stable else "-"
        return {"Windows": {"stable": stable_version, "beta": "-", "beta_release_date": "-"}}
    except Exception as e:
        print(f"Windows scrape error: {e}")
        return {"Windows": {"stable": "-", "beta": "-", "beta_release_date": "-"}}

def scrape_chrome_versions():
    try:
        url = "https://chromiumdash.appspot.com/schedule"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table")
        stable, beta = "-", "-"
        beta_release_date = "-"
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    channel = cols[0].text.strip()
                    version = cols[1].text.strip()
                    date = cols[2].text.strip()
                    if "Stable" in channel:
                        stable = version
                    elif "Beta" in channel:
                        beta = version
                        beta_release_date = date
        return {"ChromeOS": {"stable": stable, "beta": beta, "beta_release_date": beta_release_date}}
    except Exception as e:
        print(f"ChromeOS scrape error: {e}")
        return {"ChromeOS": {"stable": "-", "beta": "-", "beta_release_date": "-"}}

def load_history():
    ensure_data_folder()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_history(data):
    ensure_data_folder()
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def detect_changes(old_data, new_data):
    changes = {}
    for os_name in OS_LIST:
        old = old_data.get(os_name, {})
        new = new_data.get(os_name, {})
        for key in ["stable", "beta", "beta_release_date"]:
            if old.get(key) != new.get(key):
                changes[os_name] = new
    return changes

def send_email(data, changes):
    msg = EmailMessage()
    msg["Subject"] = f"Daily OS Versions - {datetime.now().strftime('%d %b %Y')}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    # Short summary
    summary = "🆕 Daily OS Version Updates\n"
    for os_name, info in changes.items():
        summary += f"🆕 {os_name} update: Stable: {info.get('stable', '-')}, Beta: {info.get('beta', '-')}, Beta_release_date: {info.get('beta_release_date', '-')}\n"

    # Table
    table = "Platform\tStable\tBeta\tBeta Release Date\n"
    for os_name in OS_LIST:
        info = data.get(os_name, {})
        table += f"{os_name}\t{info.get('stable', '-')}\t{info.get('beta', '-')}\t{info.get('beta_release_date', '-')}\n"

    msg.set_content(summary + "\n" + table)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_FROM, SMTP_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully")
    except Exception as e:
        print(f"Email send error: {e}")

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
