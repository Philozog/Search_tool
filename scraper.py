"""
Cash-flow business scraper — New England (BizBuySell)
Uses undetected-chromedriver to bypass Cloudflare bot detection.

Setup:
    python -m venv .venv && .venv/Scripts/activate  # Windows
    pip install -r requirements.txt
    cp .env.example .env   # fill in your Gmail credentials
"""

import os, re, time, random, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ────────────────────────────────────────────────────────────────────
SENDER_EMAIL   = os.getenv("SENDER_EMAIL", "")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")
APP_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD", "")

# ── Target business types ─────────────────────────────────────────────────────
BUSINESSES = [
    # HVAC
    "hvac", "air conditioning", "heating", "cooling", "furnace", "heat pump",
    # Roofing
    "roofing", "roofer", "roof repair",
    # Waste management
    "waste management", "waste", "garbage", "hauling", "junk removal",
    "dumpster", "sanitation", "trash",
    # Plumbing
    "plumbing", "plumber", "drain", "sewer", "septic",
]

# ── Geography ─────────────────────────────────────────────────────────────────
NE_PATTERN = re.compile(
    r'\b(connecticut|maine|massachusetts|new hampshire|rhode island|vermont'
    r'|ct|me|ma|nh|ri|vt'
    r'|boston|providence|hartford|worcester|springfield|manchester'
    r'|portland|burlington|concord|new haven|bridgeport|lowell|cambridge'
    r'|new england)\b',
    re.IGNORECASE,
)

NE_URLS = {
    "Massachusetts": "https://www.bizbuysell.com/massachusetts-businesses-for-sale/",
    "Connecticut":   "https://www.bizbuysell.com/connecticut-businesses-for-sale/",
    "Maine":         "https://www.bizbuysell.com/maine-businesses-for-sale/",
    "New Hampshire": "https://www.bizbuysell.com/new-hampshire-businesses-for-sale/",
    "Rhode Island":  "https://www.bizbuysell.com/rhode-island-businesses-for-sale/",
    "Vermont":       "https://www.bizbuysell.com/vermont-businesses-for-sale/",
}

# ── Filters ───────────────────────────────────────────────────────────────────
def matches_business(title: str, description: str) -> bool:
    text = (title + " " + description).lower()
    return any(b in text for b in BUSINESSES)

def is_new_england(location: str) -> bool:
    return bool(NE_PATTERN.search(location))

def parse_price(s: str) -> int:
    if not s:
        return 0
    s = s.replace(",", "").replace("$", "").strip().upper()
    try:
        if "M" in s:
            return int(float(s.replace("M", "")) * 1_000_000)
        if "K" in s:
            return int(float(s.replace("K", "")) * 1_000)
        return int(float(s))
    except ValueError:
        return 0

def is_under_2m(price_str: str) -> bool:
    p = parse_price(price_str)
    return p == 0 or p < 2_000_000  # unknown price passes through

# ── Browser helpers ───────────────────────────────────────────────────────────
def make_driver() -> uc.Chrome:
    opts = uc.ChromeOptions()
    opts.add_argument("--window-size=1280,900")
    # opts.add_argument("--headless=new")  # uncomment to run without a window
    driver = uc.Chrome(options=opts, version_main=147)
    driver.set_page_load_timeout(30)
    return driver

def _pause(lo=1.5, hi=3.5):
    time.sleep(random.uniform(lo, hi))

def _scroll(driver, steps=4):
    for _ in range(steps):
        driver.execute_script("window.scrollBy(0, window.innerHeight * 0.6);")
        time.sleep(random.uniform(0.4, 0.9))

# ── BizBuySell card parser ────────────────────────────────────────────────────
_CARD_SEL  = ("div.featured-listing, div.organic-listing, "
              "div[class*='listing-item'], article[data-listing-id], "
              "div[data-listing-id], .listing-card")
_TITLE_SEL = "h2, h3, a[class*='title'], [class*='bizName']"
_LOC_SEL   = "[class*='location'], [class*='city'], [class*='region']"
_PRICE_SEL = "[class*='price'], [class*='asking'], [class*='Price']"
_DESC_SEL  = "[class*='description'], [class*='snippet'], p"

def _parse_bbs_cards(soup: BeautifulSoup, state: str) -> list[dict]:
    cards = soup.select(_CARD_SEL)

    if not cards:
        # Fallback: any <a> that points to a BizBuySell listing URL
        results, seen = [], set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not any(p in href for p in ["/Business-Opportunity/", "/businesses/"]):
                continue
            url = href if href.startswith("http") else "https://www.bizbuysell.com" + href
            if url in seen:
                continue
            seen.add(url)
            parent    = a.find_parent("div") or a
            title     = (a.find("h2") or a.find("h3") or a).get_text(strip=True)
            location  = (parent.select_one(_LOC_SEL) or object()).get_text(strip=True) if parent.select_one(_LOC_SEL) else state
            price_str = (parent.select_one(_PRICE_SEL) or object()).get_text(strip=True) if parent.select_one(_PRICE_SEL) else "N/A"
            desc      = (parent.select_one(_DESC_SEL) or object()).get_text(strip=True) if parent.select_one(_DESC_SEL) else ""
            if title:
                results.append({"source": "BizBuySell", "title": title,
                                 "location": location, "description": desc,
                                 "price": price_str, "url": url})
        return results

    results = []
    for card in cards:
        title_tag = card.select_one(_TITLE_SEL)
        loc_tag   = card.select_one(_LOC_SEL)
        desc_tag  = card.select_one(_DESC_SEL)
        price_tag = card.select_one(_PRICE_SEL)
        link_tag  = card.select_one("a[href]")
        href      = (link_tag["href"] if link_tag else "")
        title     = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            continue
        results.append({
            "source":      "BizBuySell",
            "title":       title,
            "location":    loc_tag.get_text(strip=True)   if loc_tag   else state,
            "description": desc_tag.get_text(strip=True)  if desc_tag  else "",
            "price":       price_tag.get_text(strip=True) if price_tag else "N/A",
            "url":         href if href.startswith("http") else "https://www.bizbuysell.com" + href,
        })
    return results

# ── Scrapers ──────────────────────────────────────────────────────────────────
def scrape_bizbuysell(driver: uc.Chrome) -> list[dict]:
    listings = []
    for state, url in NE_URLS.items():
        print(f"  [BizBuySell] {state}...")
        try:
            driver.get(url)
            _pause(2, 4)
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, _CARD_SEL))
                )
            except Exception:
                print(f"    ⚠ timeout — parsing whatever loaded")
            _scroll(driver)
            soup  = BeautifulSoup(driver.page_source, "html.parser")
            found = _parse_bbs_cards(soup, state)
            print(f"    → {len(found)} raw")
            listings.extend(found)
            _pause(2, 3)
        except Exception as e:
            print(f"    error: {e}")
    return listings

# ── Email ─────────────────────────────────────────────────────────────────────
def send_email(listings: list[dict]) -> None:
    if not APP_PASSWORD:
        print("⚠  Set GMAIL_APP_PASSWORD to enable email.")
        return
    msg = MIMEMultipart()
    msg["Subject"] = f"{len(listings)} Cash-Flow Businesses — New England"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    body = "\n".join(
        f"[{b['source']}] {b['title']}\n"
        f"Location: {b['location']}  |  Price: {b.get('price','N/A')}\n"
        f"URL:      {b['url']}\n" + "-" * 50
        for b in listings
    ) or "No matches found today."
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(SENDER_EMAIL, APP_PASSWORD)
        s.send_message(msg)
    print(f"✅ Email sent — {len(listings)} listings.")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    driver = make_driver()
    try:
        raw = scrape_bizbuysell(driver)
    finally:
        try:
            driver.quit()
        except OSError:
            pass  # handle Windows cleanup issues with undetected-chromedriver

    filtered = [
        b for b in raw
        if matches_business(b["title"], b["description"])
        and is_new_england(b["location"])
        and is_under_2m(b.get("price", "N/A"))
    ]

    print(f"\n{'='*60}")
    print(f"Raw: {len(raw)}  |  Matched: {len(filtered)}\n")
    for b in filtered:
        print(f"  [{b['source']}] {b['title']} — {b['location']} — {b.get('price','N/A')}")
        print(f"    {b['url']}")

    # send_email(filtered)  # uncomment when ready
