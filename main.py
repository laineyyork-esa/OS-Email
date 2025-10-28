import requests
from bs4 import BeautifulSoup
import json
from dateutil import parser as dateparser
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
    """Scrape macOS and iPadOS versions from Apple Developer RSS feed."""
    versions = {"macOS": {}, "iPadOS": {}}
    rss_url = "https://developer.apple.com/news/rss/news.rss"
    resp = requests.get(rss_url)
    soup = BeautifulSoup(resp.content, "xml")
    items = soup.find_all("item")

    for os_name in versions.keys():
        for item in items:
            title = item.title.text
            pub_date = item.pubDate.text
            if os_name in title:
                if "beta" in title.lower():
                    versions[os_name]["beta"] = title.replace("is now available", "").strip()
                    versions[os_name]["beta_release_date"] = dateparser.parse(pub_date).strftime("%d %b %Y")
                elif any(x in title.lower() for x in ["released", "available"]) and "beta" not in title.lower():
                    versions[os_name]["stable"] = title.replace("is now available", "").strip()

        versions[os_name].setdefault("stable", "-")
        versions[os_name].setdefault("beta", "-")
        versions[os_name].setdefault("beta_release_date", "-")

    return versions

def scrape_windows_versions():
    """Scrape Windows stable version from Microsoft release health page."""
    url = "https://learn.microsoft.com/en-us/windows/release-health/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    version = "-"
    try:
        # Capture "Windows 11, version 25H2" or similar
        heading = soup.find(["h2", "h3"], string=lambda x: x and "Windows 11" in x)
        if heading:
            version = heading.text.strip()
    except Exception:
        pass

    return {"Windows": {"stable": version, "beta": "-", "beta_release_date": "-"}}


def scrape_chromeos_versions():
    """Scrape ChromeOS versions and beta release date from Chromium Dash."""
    try:
        url = "https://chromiumdash.appspot.com/fetch_milestone_schedule"
        data = requests.get(url).json()

        # Find latest stable and beta milestones
        stable = next((x for x in data if x.get("channel") == "Stable"), {})
        beta = next((x for x in data if x.get("channel") == "Beta"), {})

        stable_version = stable.get("milestone", "-")
        beta_version = beta.get("milestone", "-")

        # Prefer beta_promotion date
        beta_date = beta.get("beta_promotion", "") or beta.get("branch_point", "-")
        if beta_date:
            try:
                beta_date = datetime.strptime(beta_date, "%Y-%m-%d").strftime("%d %b %Y")
            except Exception:
                pass

        return {
            "ChromeOS": {
                "stable": f"Chrome {stable_version}",
                "beta": f"Chrome {beta_version}",
                "beta_release_date": beta_date or "-",
            }
        }
    except Exception as e:
        print("ChromeOS scrape error:", e)
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
