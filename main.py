# main.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

def scrape_apple_versions():
    url = "https://developer.apple.com/news/releases/"
    data = {"macOS": {}, "iPadOS": {}}
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.find_all("article")

        for article in articles:
            title_tag = article.find("h2")
            date_tag = article.find("time")
            if not title_tag or not date_tag:
                continue
            title = title_tag.get_text(strip=True)
            date = date_tag.get_text(strip=True)

            # Parse versions
            if "macOS" in title:
                match = re.search(r"macOS\s+([0-9\.]+)\s*(beta\s*[0-9]*)?", title, re.IGNORECASE)
                if match:
                    data["macOS"]["stable"] = match.group(1) if "beta" not in title.lower() else "-"
                    data["macOS"]["beta"] = match.group(2) if match.group(2) else "-"
                    data["macOS"]["beta_release_date"] = datetime.strptime(date, "%B %d, %Y").strftime("%d %b %Y")
            elif "iPadOS" in title:
                match = re.search(r"iPadOS\s+([0-9\.]+)\s*(beta\s*[0-9]*)?", title, re.IGNORECASE)
                if match:
                    data["iPadOS"]["stable"] = match.group(1) if "beta" not in title.lower() else "-"
                    data["iPadOS"]["beta"] = match.group(2) if match.group(2) else "-"
                    data["iPadOS"]["beta_release_date"] = datetime.strptime(date, "%B %d, %Y").strftime("%d %b %Y")
    except Exception as e:
        print(f"Apple scrape error: {e}")
    return data

def scrape_windows_versions():
    url = "https://learn.microsoft.com/en-us/windows/release-health/"
    data = {"Windows": {}}
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for version text
        stable_tag = soup.find(string=re.compile(r"Windows 11.*"))
        if stable_tag:
            data["Windows"]["stable"] = stable_tag.strip()
        else:
            data["Windows"]["stable"] = "-"

        data["Windows"]["beta"] = "-"  # Optional: can add beta parsing if needed
        data["Windows"]["beta_release_date"] = "-"
    except Exception as e:
        print(f"Windows scrape error: {e}")
    return data

def scrape_chrome_versions():
    data = {"ChromeOS": {}}
    try:
        url = "https://developer.chrome.com/release-notes"
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Get stable version
        stable_tag = soup.find(string=re.compile(r"Chrome\s+\d+"))
        data["ChromeOS"]["stable"] = stable_tag.strip() if stable_tag else "-"
        
        # Get beta version
        beta_tag = soup.find(string=re.compile(r"Chrome\s+\d+\s+Beta"))
        data["ChromeOS"]["beta"] = beta_tag.strip() if beta_tag else "-"
        data["ChromeOS"]["beta_release_date"] = "-"  # Can extend to scrape from Chromium Dash
    except Exception as e:
        print(f"ChromeOS scrape error: {e}")
    return data

def main():
    data = {}
    data.update(scrape_apple_versions())
    data.update(scrape_windows_versions())
    data.update(scrape_chrome_versions())

    print("\nOS Versions Table:")
    for os_name, details in data.items():
        print(f"{os_name}: {details}")

if __name__ == "__main__":
    main()
