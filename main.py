import requests
from bs4 import BeautifulSoup
import json
import smtplib
import os
import re
from datetime import datetime, timedelta
from dateutil import parser as dateparser
import warnings
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

warnings.filterwarnings("ignore", category=UserWarning, module='dateutil.parser')

HISTORY_FILE = "data/os_versions.json"
RECIPIENT = "lainey.york@esa.edu.au"

# -----------------------------------------------------------
# APPLE SCRAPER
# -----------------------------------------------------------
def scrape_apple_versions():
    """Scrape macOS and iPadOS versions from Apple Developer RSS feed."""
    versions = {"macOS": {}, "iPadOS": {}}
    rss_url = "https://developer.apple.com/news/rss/news.rss"
    resp = requests.get(rss_url)
    soup = BeautifulSoup(resp.content, "xml")
    items = soup.find_all("item")

    for os_name in versions.keys():
        beta_found = False
        stable_found = False

        for item in items:
            title = item.title.text.strip()
            pub_date = item.pubDate.text.strip()

            # Match beta posts like: "macOS 26.1 beta 4 (25B5072a) now available"
            if os_name in title and "beta" in title.lower() and not beta_found:
                match = re.search(rf"{os_name}\s[\d\.]+\s.*?beta.*?\)", title, re.IGNORECASE)
                versions[os_name]["beta"] = match.group(0) if match else title
                versions[os_name]["beta_release_date"] = dateparser.parse(pub_date).strftime("%d %b %Y")
                beta_found = True

            # Match stable posts like: "macOS 26.1 now available"
            elif os_name in title and "beta" not in title.lower() and not stable_found:
                match = re.search(rf"{os_name}\s[\d\.]+", title)
                versions[os_name]["stable"] = match.group(0).replace(os_name, "").strip() if match else title
                stable_found = True

        versions[os_name].setdefault("stable", "-")
        versions[os_name].setdefault("beta", "-")
        versions[os_name].setdefault("beta_release_date", "-")

    return versions

# -----------------------------------------------------------
# WINDOWS SCRAPER
# -----------------------------------------------------------
def scrape_windows_versions():
    """Scrape latest Windows version from Microsoft release health."""
    url = "https://learn.microsoft.com/en-us/windows/release-health/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    stable_version = "-"
    heading = soup.find("h2", string=re.compile("Windows 11"))
    if heading:
        text = heading.get_text(strip=True)
        match = re.search(r"Windows\s11[, ]+version\s[\dH]+", text)
        if match:
            stable_version = match.group(0)

    return {"Windows": {"stable": stable_version, "beta": "-", "beta_release_date": "-"}}

# -----------------------------------------------------------
# CHROMEOS SCRAPER
# -----------------------------------------------------------
def scrape_chromeos_versions():
    """Scrape ChromeOS versions and beta release date from Chromium Dash."""
    try:
        url = "https://chromiumdash.appspot.com/fetch_milestone_schedule"
        response = requests.get(url)
        data = response.json()

        if isinstance(data, dict):
            data = [data]

        stable = next((x for x in data if x.get("channel", "").lower() == "stable"), {})
        beta = next((x for x in data if x.get("channel", "").lower() == "beta"), {})

        stable_version = stable.get("milestone", "-")
        beta_version = beta.get("milestone", "-")

        beta_date = beta.get("beta_promotion", "") or beta.get("branch_point", "-")
        if beta_date:
            try:
                beta_date = datetime.strptime(beta_date, "%Y-%m-%d").strftime("%d %b %Y")
            except Exception:
                pass

        return {
            "ChromeOS": {
                "stable": f"Chrome {stable_version}" if stable_version != "-" else "-",
                "beta": f"Chrome {beta_version}" if beta_version != "-" else "-",
                "beta_release_date": beta_date or "-",
            }
        }

    except Exception as e:
        print("ChromeOS scrape error:", e)
        return {"ChromeOS": {"stable": "-", "beta": "-", "beta_release_date": "-"}}

# -----------------------------------------------------------
# HISTORY HANDLING
# -----------------------------------------------------------
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def save_history(data):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    history[today] = data

    # Keep only 7 days
    if len(history) > 7:
        for k in sorted(history.keys())[:-7]:
            del history[k]

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# -----------------------------------------------------------
# CHANGE DETECTION
# -----------------------------------------------------------
def detect_changes(history, current_data):
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    previous = history.get(yesterday, {})
    changes = []

    for os_name, vals in current_data.items():
        if os_name not in previous:
            changes.append(f"🆕 {os_name} update: Stable: {vals['stable']}, Beta: {vals['beta']}, Beta_release_date: {vals['beta_release_date']}")
            continue

        for key in vals:
            if vals[key] != previous[os_name].get(key):
                changes.append(f"🆕 {os_name} update: Stable: {vals['stable']}, Beta: {vals['beta']}, Beta_release_date: {vals['beta_release_date']}")
                break

    return changes

# -----------------------------------------------------------
# EMAIL COMPOSITION
# -----------------------------------------------------------
def send_email(subject, body, html_table):
    sender = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_PASS")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = RECIPIENT

    text_part = MIMEText(body, "plain")
    html_part = MIMEText(html_table, "html")

    msg.attach(text_part)
    msg.attach(html_part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
def main():
    data = {}
    data.update(scrape_apple_versions())
    data.update(scrape_windows_versions())
    data.update(scrape_chromeos_versions())

    history = load_history()
    changes = detect_changes(history, data)
    save_history(data)

    # Build table
    html_table = """
    <html><body>
    <h2>Daily OS Versions</h2>
    <table border="1" cellspacing="0" cellpadding="4">
      <tr><th>Platform</th><th>Stable</th><th>Beta</th><th>Beta Release Date</th></tr>
    """
    for os_name, vals in data.items():
        html_table += f"<tr><td>{os_name}</td><td>{vals['stable']}</td><td>{vals['beta']}</td><td>{vals['beta_release_date']}</td></tr>"
    html_table += "</table><br><p><i>Last updated: {}</i></p></body></html>".format(datetime.now().strftime("%d %b %Y %H:%M AEST"))

    summary = "\n".join(changes) if changes else "No new updates in the past 24 hours."
    subject = f"Daily OS Version Report - {datetime.now().strftime('%d %b %Y')}"

    send_email(subject, summary, html_table)
    print("Email sent successfully.")

if __name__ == "__main__":
    main()
