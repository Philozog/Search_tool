"""
Cash-flow business scraper — New England
Uses undetected-chromedriver to bypass bot detection on BizBuySell & Craigslist.

Install deps first:
    pip install undetected-chromedriver selenium beautifulsoup4
"""

import time
import random
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ────────────────────────────────────────────────────────────────────
SENDER_EMAIL   = os.getenv("SENDER_EMAIL",       "philippe.zoghzoghi@gmail.com")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL",     "philippe.zoghzoghi@gmail.com")
APP_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD", "")  # set env var, never hardcode

# ── Data ──────────────────────────────────────────────────────────────────────
NEW_ENGLAND = [
    "connecticut", "maine", "massachusetts", "new hampshire",
    "rhode island", "vermont",
    "boston", "providence", "hartford", "manchester", "portland",
    "burlington", "concord", "springfield", "worcester", "lowell",
    "cambridge", "new haven", "bridgeport", " ct", " me", " ma",
    " nh", " ri", " vt",
]

BUSINESSES = [
    "hvac", "plumbing", "electrical", "landscaping", "cleaning",
    "pest control", "handyman", "lawn care", "snow removal",
    "pool maintenance", "roofer", "roofing", "auto mechanic", "carpentry",
    "painting", "moving", "tutoring", "personal training",
    "pet care", "childcare", "elderly care", "laundry",
    "pressure washing", "junk removal", "window cleaning",
]

# ── Filters ───────────────────────────────────────────────────────────────────
def matches_business(title: str, description: str) -> bool:
    text = (title + " " + description).lower()
    return any(b in text for b in BUSINESSES)

def is_new_england(location: str) -> bool:
    loc = location.lower()
    return any(place in loc for place in NEW_ENGLAND)

# ── Browser ───────────────────────────────────────────────────────────────────
def make_driver() -> uc.Chrome:
    """
    undetected_chromedriver patches Chrome so Cloudflare / bot-detection
    can't fingerprint it as automated. Requires Chrome to be installed.
    """
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,900")
    # Remove the comment below to run headless (no visible window):
    # options.add_argument("--headless=new")
    driver = uc.Chrome(options=options, version_main=None)  # auto-detects Chrome version
    driver.set_page_load_timeout(30)
    return driver

def _pause(lo=1.5, hi=3.5):
    time.sleep(random.uniform(lo, hi))

def _scroll(driver, times=3):
    """Scroll down gradually to trigger lazy-loaded content."""
    for _ in range(times):
        driver.execute_script("window.scrollBy(0, window.innerHeight * 0.7);")
        _pause(0.5, 1.2)

# ── Scrapers ──────────────────────────────────────────────────────────────────

def scrape_craigslist(driver: uc.Chrome) -> list[dict]:
    listings = []

    regions = [
        ("boston",        "https://boston.craigslist.org/search/bfs"),
        ("providence",    "https://providence.craigslist.org/search/bfs"),
        ("hartford",      "https://hartford.craigslist.org/search/bfs"),
        ("newhavenct",    "https://newhavenct.craigslist.org/search/bfs"),
        ("maine",         "https://maine.craigslist.org/search/bfs"),
        ("vermont",       "https://vermont.craigslist.org/search/bfs"),
        ("newhampshire",  "https://newhampshire.craigslist.org/search/bfs"),
        ("rhodeisland",   "https://rhodeisland.craigslist.org/search/bfs"),
    ]

    for region_name, url in regions:
        print(f"  [Craigslist] Scraping {region_name}...")
        try:
            driver.get(url)
            _pause()
            _scroll(driver)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Current markup (2024-2025)
            items = soup.select("li.cl-search-result")
            # Fallback to older markup
            if not items:
                items = soup.select(".result-row")

            before = len(listings)
            for item in items:
                title_tag = (
                    item.select_one("a.posting-title span.label") or
                    item.select_one("a.posting-title") or
                    item.select_one(".result-title")
                )
                hood_tag = (
                    item.select_one("span.hood") or
                    item.select_one(".result-hood")
                )
                link_tag = (
                    item.select_one("a.posting-title") or
                    item.select_one("a.result-title")
                )

                title    = title_tag.get_text(strip=True) if title_tag else ""
                location = hood_tag.get_text(strip=True).strip("() ") if hood_tag else region_name
                href     = link_tag["href"] if link_tag else ""

                if title:
                    listings.append({
                        "source":      f"Craigslist ({region_name})",
                        "title":       title,
                        "location":    location or region_name,
                        "description": "",
                        "url":         href,
                    })

            print(f"    → {len(listings) - before} listings")
            _pause()

        except Exception as e:
            print(f"  [Craigslist] Error on {region_name}: {e}")
            continue

    print(f"[Craigslist] Total raw listings: {len(listings)}")
    return listings


def scrape_bizbuysell(driver: uc.Chrome) -> list[dict]:
    listings = []
    ne_states = ["ct", "me", "ma", "nh", "ri", "vt"]

    for state in ne_states:
        url = f"https://www.bizbuysell.com/businesses-for-sale/{state}/"
        print(f"  [BizBuySell] Scraping {state.upper()}...")

        try:
            driver.get(url)
            _pause(2, 4)

            # Wait for listing cards to appear
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        "a[data-testid='listing-title'], .bizListingTitle, h2.title, .listing"))
                )
            except Exception:
                print(f"    ⚠️  Timed out waiting for listings on {state.upper()}")

            _scroll(driver)
            _pause()

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Try multiple possible selectors (BizBuySell changes these often)
            cards = (
                soup.select("article[data-listing-id]") or
                soup.select("div[data-listing-id]") or
                soup.select(".listing-card") or
                soup.select(".bizListingBox") or
                soup.select("li.listing")
            )

            before = len(listings)
            for card in cards:
                title_tag = (
                    card.select_one("a[data-testid='listing-title']") or
                    card.select_one("h2") or
                    card.select_one("h3") or
                    card.select_one(".bizListingTitle") or
                    card.select_one(".title a")
                )
                loc_tag = (
                    card.select_one("[data-testid='listing-location']") or
                    card.select_one(".listing-location") or
                    card.select_one(".location")
                )
                desc_tag = (
                    card.select_one("[data-testid='listing-description']") or
                    card.select_one(".listing-description") or
                    card.select_one("p")
                )
                link_tag = card.select_one("a[href]")

                title       = title_tag.get_text(strip=True) if title_tag  else ""
                location    = loc_tag.get_text(strip=True)   if loc_tag    else state.upper()
                description = desc_tag.get_text(strip=True)  if desc_tag   else ""
                href        = link_tag["href"]               if link_tag   else ""

                if title:
                    listings.append({
                        "source":      "BizBuySell",
                        "title":       title,
                        "location":    location or state.upper(),
                        "description": description,
                        "url":         href if href.startswith("http") else "https://www.bizbuysell.com" + href,
                    })

            print(f"    → {len(listings) - before} listings")
            _pause(2, 4)

        except Exception as e:
            print(f"  [BizBuySell] Error on {state}: {e}")
            continue

    print(f"[BizBuySell] Total raw listings: {len(listings)}")
    return listings


# ── Email ─────────────────────────────────────────────────────────────────────
def send_email(listings: list[dict]) -> None:
    if not APP_PASSWORD:
        print("⚠️  GMAIL_APP_PASSWORD env var not set — skipping email.")
        return

    msg = MIMEMultipart()
    msg["Subject"] = f"🔥 {len(listings)} Cash-Flow Businesses in New England"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL

    body = ""
    if listings:
        for biz in listings:
            body += (
                f"Title:    {biz['title']}\n"
                f"Source:   {biz['source']}\n"
                f"Location: {biz['location']}\n"
                f"Desc:     {biz['description'][:200]}\n"
                f"URL:      {biz['url']}\n"
                + "-" * 50 + "\n"
            )
    else:
        body = "No matching businesses found today."

    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
    print(f"✅ Email sent with {len(listings)} listings.")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    driver = make_driver()

    try:
        all_listings = []
        all_listings += scrape_craigslist(driver)
        all_listings += scrape_bizbuysell(driver)
    finally:
        driver.quit()

    filtered = [
        biz for biz in all_listings
        if matches_business(biz["title"], biz["description"])
        and is_new_england(biz["location"])
    ]

    print(f"\n✅ {len(filtered)} matching businesses after filtering:\n")
    for biz in filtered:
        print(f"  [{biz['source']}] {biz['title']} — {biz['location']}")
        if biz.get("url"):
            print(f"    {biz['url']}")

    # Uncomment when ready to receive emails:
    # send_email(filtered)