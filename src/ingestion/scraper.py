"""Web scraper module for fetching mutual fund data from Groww."""
import os
import time
import logging
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

URLS = [
    "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
]

def is_js_rendered(html: str) -> bool:
    """Heuristic to check if page is mostly JS rendered (missing core content)."""
    soup = BeautifulSoup(html, "html.parser")
    # If the body is very small or has no text, it's likely JS rendered
    text_content = soup.get_text(strip=True)
    if len(text_content) < 500:
        return True
    
    # Check for common React root elements which might be empty
    root = soup.find(id="root")
    if root and not root.text.strip():
        return True
        
    return False

def fetch_with_requests(url: str) -> str:
    """Fetch HTML content using the requests library."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def fetch_with_playwright(url: str) -> str:
    """Fetch HTML content using Playwright as a fallback."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Navigate and wait for network to be idle
        page.goto(url, wait_until="networkidle")
        # Additionally, waiting for a short duration to allow dynamic rendering
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()
        return html

def fetch_html(url: str) -> str:
    """Fetch HTML from a URL, falling back to Playwright if requests fails."""
    logger.info(f"Attempting to fetch {url} with requests...")
    try:
        html = fetch_with_requests(url)
        if is_js_rendered(html):
            logger.info("Page seems JS-rendered. Falling back to Playwright...")
            html = fetch_with_playwright(url)
        else:
             logger.info("Successfully fetched content with requests.")
        return html
    except Exception as e:
        logger.warning(f"Requests failed: {e}. Falling back to Playwright...")
        return fetch_with_playwright(url)

def run_scraper():
    # Ensure data/raw directory exists relative to the project root
    # Since this script will likely be run from the project root using `python -m src.ingestion.scraper`
    # or `python -m src.ingestion.run_ingestion`, we use `data/raw`
    """Run the scraper on the configured URLs and save raw HTML."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    raw_dir = os.path.join(base_dir, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    
    logger.info(f"Saving raw HTML files to {raw_dir}")
    
    for url in URLS:
        try:
            html = fetch_html(url)
            
            # Extract scheme name from URL
            path = urlparse(url).path
            scheme_name = path.split("/")[-1]
            timestamp = int(time.time())
            
            filename = f"{scheme_name}_{timestamp}.html"
            filepath = os.path.join(raw_dir, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
                
            logger.info(f"Successfully saved {filename}")
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")

if __name__ == "__main__":
    run_scraper()
