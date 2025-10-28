import requests
from bs4 import BeautifulSoup
from datetime import datetime

# -------------------------------
# CONFIGURATION
# -------------------------------
PLATFORMS = ["macOS", "iPadOS", "Windows", "ChromeOS"]

# -------------------------------
# SCRAPERS
# -------------------------------

def scrape_apple_versions():
    versions = {"macOS": {}, "iPadOS": {}}
    rss_url = "https://developer.apple.com/news/rss/news.rss"
    try:
        resp = requests.get(rss_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        items = soup.find_all("item")
        for item in items[:5]:  # check first 5 items for beta releases
            title = item.title.text
            pub_date = item.pubDate.text
            # parse date
            try:
                release_date = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z").strftime("%d %b %Y")
            except:
                release_date = pub_date
            if "macOS" in title:
                versions["macOS"]["beta"] = title
                versions["macOS"]["beta_release_date"] = release_date
            elif "iPadOS" in title:
                versions["iPadOS"]["beta"] = title
                versions["iPadOS"]["beta_release_date"] = release_date
        # For demo, Stable version can be hardcoded or fetched from separate page
        versions["macOS"]["stable"] = "26.1"
        versions["iPadOS"]["stable"] = "26.0.1"
    except Exception as e:
        print("Apple scrape error:", e)
        for os_name in ["macOS", "iPadOS"]:
            versions[os_name] = {"stable": "-", "beta": "-", "beta_release_date": "-"}
    return versions

def scrape_windows_versions():
    versions = {"Windows": {}}
    url = "https://learn.microsoft.com/en-us/windows/release-health/"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        # Simplified: manually parse latest Windows 11 release
        versions["Windows"]["stable"] = "Windows 11 25H5"
        versions["Windows"]["beta"] = "-"
        versions["Windows"]["beta_release_date"] = "-"
    except Exception as e:
        print("Windows scrape error:", e)
        versions["Windows"] = {"stable": "-", "beta": "-", "beta_release_date": "-"}
    return versions

def scrape_chrome_versions():
    versions = {"ChromeOS": {}}
    url = "https://chromiumdash.appspot.com/schedule"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Simplified demo: hardcode Chrome beta info
        versions["ChromeOS"]["stable"] = "Chrome 141"
        versions["ChromeOS"]["beta"] = "Chrome 142"
        versions["ChromeOS"]["beta_release_date"] = "28 Oct 2025"
    except Exception as e:
        print("ChromeOS scrape error:", e)
        versions["ChromeOS"] = {"stable": "-", "beta": "-", "beta_release_date": "-"}
    return versions

# -------------------------------
# MAIN
# -------------------------------

def main():
    data = {}
    data.update(scrape_apple_versions())
    data.update(scrape_windows_versions())
    data.update(scrape_chrome_versions())

    # Print nicely for console verification
    print(f"\nDaily OS Versions - {datetime.now().strftime('%d %b %Y')}")
    print("="*30)
    print("\nPlatform\tStable\tBeta\tBeta Release Date")
    for platform in PLATFORMS:
        stable = data.get(platform, {}).get("stable", "-")
        beta = data.get(platform, {}).get("beta", "-")
        beta_date = data.get(platform, {}).get("beta_release_date", "-")
        print(f"{platform}\t{stable}\t{beta}\t{beta_date}")

if __name__ == "__main__":
    main()
