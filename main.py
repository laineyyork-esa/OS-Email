import os
from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup
import dateparser

# Paths
HISTORY_FILE = "data/os_versions.json"

# Initialize OS data
OS_LIST = ["macOS", "iPadOS", "Windows", "ChromeOS"]

def ensure_data_folder():
    if not os.path.exists("data"):
        os.makedirs("data")

def scrape_apple_versions():
    url = "https://developer.apple.com/news/rss/news.rss"
    versions = {"macOS": {}, "iPadOS": {}}
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")
        for item in items:
            title = item.title.text
            pub_date = item.pubDate.text
            if "macOS" in title:
                versions["macOS"]["beta"] = title
                versions["macOS"]["beta_release_date"] = dateparser.parse(pub_date).strftime("%d %b %Y")
            elif "iPadOS" in title:
                versions["iPadOS"]["beta"] = title
                versions["iPadOS"]["beta_release_date"] = dateparser.parse(pub_date).strftime("%d %b %Y")
    except Exception as e:
        print(f"Apple scrape error: {e}")
    return versions

def scrape_windows_versions():
    versions = {"Windows": {"stable": "-", "beta": "-", "beta_release_date": "-"}}
    try:
        url = "https://learn.microsoft.com/en-us/windows/release-health/"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        stable = soup.find("td", string=lambda x: "Windows 11" in x if x else False)
        if stable:
            versions["Windows"]["stable"] = stable.text.strip()
    except Exception as e:
        print(f"Windows scrape error: {e}")
    return versions

def scrape_chrome_versions():
    versions = {"ChromeOS": {"stable": "-", "beta": "-", "beta_release_date": "-"}}
    try:
        url = "https://chromiumdash.appspot.com/schedule"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    channel = cols[0].text.strip()
                    version = cols[1].text.strip()
                    date = cols[2].text.strip()
                    if "Stable" in channel:
                        versions["ChromeOS"]["stable"] = version
                    elif "Beta" in channel:
                        versions["ChromeOS"]["beta"] = version
                        versions["ChromeOS"]["beta_release_date"] = date
    except Exception as e:
        print(f"ChromeOS scrape error: {e}")
    return versions

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

def main():
    data = {}
    data.update(scrape_apple_versions())
    data.update(scrape_windows_versions())
    data.update(scrape_chrome_versions())

    history = load_history()
    changes = detect_changes(history, data)
    save_history(data)

    # === Print email content instead of sending email ===
    print("\n======================")
    print(f"Daily OS Versions - {datetime.now().strftime('%d %b %Y')}")
    print("======================\n")
    print("🆕 Short summary of changes:")
    for os_name, info in changes.items():
        print(f"🆕 {os_name} update: Stable: {info.get('stable','-')}, Beta: {info.get('beta','-')}, Beta Release Date: {info.get('beta_release_date','-')}")

    print("\nPlatform\tStable\tBeta\tBeta Release Date")
    for os_name in OS_LIST:
        info = data.get(os_name, {})
        print(f"{os_name}\t{info.get('stable','-')}\t{info.get('beta','-')}\t{info.get('beta_release_date','-')}")

if __name__ == "__main__":
    main()
