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
    soup = Beautif
