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
