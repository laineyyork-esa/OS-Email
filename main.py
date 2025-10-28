import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# --- Config ---
HISTORY_FILE = "data/os_versions.json"
EMAIL_FROM = os.environ.get("GMAIL_USER")
EMAIL_PASS = os.environ.get("GMAIL_PASS")
EMAIL_TO = "lainey.york@esa.edu.au"

OS_PLATFORMS = ["macOS", "iPadOS", "Windows", "ChromeOS"]

# --- Scrapers ---

def scrape_apple_versions():
    """Scrapes macOS and iPadOS stable/beta versions and beta release dates."""
    versions = {}
    # RSS feed (simpler than parsing HTML)
    rss_url = "https://developer.apple.com/news/rss/news.rss"
    resp = requests.get(rss_url)
    soup = BeautifulSoup(resp.content, "xml")
    items = soup.find_all("item")
    
    for os_name in ["macOS", "iPadOS"]:
        for item in items:
            title = item.title.text
            pub_date = item.pubDate.text
            if os_name in title and "Beta" in title:
                versions[os_name] = {
                    "stable": "-",  # We'll fill later
                    "beta": title.split(":")[-1].strip(),
                    "beta_release_date": datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z").strftime("%d %b %Y")
                }
            elif os_name in title and "Stable" in title:
                versions.setdefault(os_name, {})["stable"] = title.split(":")[-1].strip()
    return versions

def scrape_windows_versions():
    """Scrapes Windows release info."""
    url = "https://learn.microsoft.com/en-us/windows/release-health/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    # Simplified example: find table row with "Windows 11" and latest version
    try:
        table = soup.find("table")
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 2 and "Windows 11" in cells[0].text:
                stable = cells[1].text.strip()
                return {"Windows": {"stable": stable, "beta": "-", "beta_release_date": "-"}}
    except Exception:
        pass
    return {"Windows": {"stable": "-", "beta": "-", "beta_release_date": "-"}}

def scrape_chromeos_versions():
    """Scrapes ChromeOS Stable/Beta and Beta release date from Chromium Dash JSON."""
    url = "https://chromiumdash.appspot.com/fetch_milestone_schedule?mstone=142"  # replace 142 with latest
    try:
        data = requests.get(url).json()
        stable_version = data.get("stable_milestone", "141")
        beta_info = data.get("beta_milestones", [{}])[-1]  # latest beta milestone
        beta_version = beta_info.get("milestone", "142")
        beta_date = beta_info.get("beta_promotion", "")
        return {"ChromeOS": {"stable": f"Chrome {stable_version}", "beta": f"Chrome {beta_version}", "beta_release_date": beta_date}}
    except Exception:
        return {"ChromeOS": {"stable": "-", "beta": "-", "beta_release_date": "-"}}

# --- Utilities ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_history(data):
    # Ensure data folder exists
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    # Keep only last 7 days
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    history[today] = data
    if len(history) > 7:
        oldest = sorted(history.keys())[0]
        del history[oldest]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def detect_changes(history, today_data):
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    changes = {}
    yesterday_data = history.get(yesterday, {})
    for os_name in OS_PLATFORMS:
        today_vals = today_data.get(os_name, {})
        yesterday_vals = yesterday_data.get(os_name, {})
        changes[os_name] = {}
        for key in ["stable", "beta", "beta_release_date"]:
            if today_vals.get(key) != yesterday_vals.get(key):
                changes[os_name][key] = today_vals.get(key)
    return changes

def build_email_html(data, changes):
    html = "<h2>Daily OS Versions</h2>"
    # Short summary
    summary_lines = []
    for os_name, vals in changes.items():
        if vals:
            line = f"🆕 {os_name} update: "
            parts = []
            for k, v in vals.items():
                parts.append(f"{k.capitalize()}: {v}")
            line += ", ".join(parts)
            summary_lines.append(line)
    if summary_lines:
        html += "<p>" + "<br>".join(summary_lines) + "</p>"
    # Table
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Platform</th><th>Stable</th><th>Beta</th><th>Beta Release Date</th></tr>"
    for os_name in OS_PLATFORMS:
        vals = data.get(os_name, {})
        html += f"<tr><td>{os_name}</td>"
        for key in ["stable", "beta", "beta_release_date"]:
            cell_val = vals.get(key, "-")
            # Highlight changes
            if changes.get(os_name, {}).get(key):
                color = "green" if key=="beta" else "yellow"
                html += f"<td style='background-color:{color}'>{cell_val}</td>"
            else:
                html += f"<td>{cell_val}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def send_email(html_content):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = "Daily OS Version Update"
    msg.attach(MIMEText(html_content, "html"))
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_FROM, EMAIL_PASS)
    server.send_message(msg)
    server.quit()

# --- Main ---
def main():
    data = {}
    data.update(scrape_apple_versions())
    data.update(scrape_windows_versions())
    data.update(scrape_chromeos_versions())
    
    history = load_history()
    changes = detect_changes(history, data)
    save_history(data)
    
    html_content = build_email_html(data, changes)
    send_email(html_content)
    print("Email sent successfully.")

if __name__ == "__main__":
    main()
