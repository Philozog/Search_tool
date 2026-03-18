"""
BizBuySell cash-flow scraper — New England
Uses undetected-chromedriver to bypass Cloudflare bot detection.

Install:
    pip install undetected-chromedriver selenium beautifulsoup4
"""

import time, random, smtplib, os, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Toggle to True on first run to print raw HTML and confirm selectors ───────
DEBUG = True

# ── Config ────────────────────────────────────────────────────────────────────
SENDER_EMAIL   = os.getenv("SENDER_EMAIL",       "philippe.zoghzoghi@gmail.com")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL",     "philippe.zoghzoghi@gmail.com")
APP_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD", "")

# ── FIXED: correct BizBuySell URL format confirmed from live site ─────────────
# Real format: https://www.bizbuysell.com/{state-name}-businesses-for-sale/
NE_URLS = {
    "Massachusetts": "https://www.bizbuysell.com/massachusetts-businesses-for-sale/",
    "Connecticut":   "https://www.bizbuysell.com/connecticut-businesses-for-sale/",
    "Maine":         "https://www.bizbuysell.com/maine-businesses-for-sale/",
    "New Hampshire": "https://www.bizbuysell.com/new-hampshire-businesses-for-sale/",
    "Rhode Island":  "https://www.bizbuysell.com/rhode-island-businesses-for-sale/",
    "Vermont":       "https://www.bizbuysell.com/vermont-businesses-for-sale/",
}

# ── NE filter — word-boundary regex so "MA" alone matches ────────────────────
NE_PATTERNS = re.compile(
    r'\b(connecticut|maine|massachusetts|new hampshire|rhode island|vermont'
    r'|ct|me|ma|nh|ri|vt'
    r'|boston|providence|hartford|worcester|springfield|manchester'
    r'|portland|burlington|concord|new haven|bridgeport|lowell|cambridge'
    r'|new england)\b',
    re.IGNORECASE
)

# ── Business keywords ─────────────────────────────────────────────────────────
BUSINESSES = [
    "hvac", "plumbing", "plumber", "electrical", "electrician",
    "landscaping", "landscape", "cleaning", "cleaner", "janitorial",
    "pest control", "exterminator", "handyman", "lawn care", "lawn service",
    "snow removal", "snow plowing", "pool maintenance", "pool service",
    "roofer", "roofing", "auto mechanic", "auto repair", "carpentry",
    "carpenter", "painting", "painter", "moving", "mover",
    "tutoring", "tutor", "personal training", "personal trainer",
    "pet care", "dog walking", "pet sitting", "childcare", "child care",
    "elderly care", "senior care", "laundry", "dry clean",
    "pressure washing", "power washing", "junk removal", "window cleaning",
    "tree service", "tree trimming", "arborist", "septic", "drain",
    "sewer", "gutter", "insulation", "flooring", "tile", "drywall",
    "masonry", "concrete", "fencing", "irrigation", "sprinkler",
    "chimney", "locksmith", "appliance repair", "garage door",
    "courier", "delivery", "air duct", "duct cleaning",
]

# ── Filters ───────────────────────────────────────────────────────────────────
def matches_business(title: str, description: str) -> bool:
    text = (title + " " + description).lower()
    return any(b in text for b in BUSINESSES)

def is_new_england(location: str) -> bool:
    return bool(NE_PATTERNS.search(location))

def parse_price(price_str: str) -> int:
    """Convert '$1,250,000' or '1.2M' or 'N/A' → integer (0 if unparseable)."""
    if not price_str:
        return 0
    s = price_str.replace(",", "").replace("$", "").strip().upper()
    try:
        if "M" in s:
            return int(float(s.replace("M", "")) * 1_000_000)
        elif "K" in s:
            return int(float(s.replace("K", "")) * 1_000)
        else:
            return int(float(s))
    except ValueError:
        return 0  # "N/A", "Call for price", etc. → treat as unknown

def is_under_2m(price_str: str) -> bool:
    """Return True if asking price is below $2,000,000 (unknown price passes through)."""
    price = parse_price(price_str)
    return price == 0 or price < 2_000_000  # 0 means unknown — don't exclude it

# ── Browser ───────────────────────────────────────────────────────────────────
def make_driver() -> uc.Chrome:
    opts = uc.ChromeOptions()
    opts.add_argument("--window-size=1280,900")
    # Uncomment to run without a visible window once confirmed working:
    # opts.add_argument("--headless=new")
    driver = uc.Chrome(options=opts, version_main=None)
    driver.set_page_load_timeout(30)
    return driver

def _pause(lo=1.5, hi=3.5):
    time.sleep(random.uniform(lo, hi))

def _scroll(driver, steps=4):
    for _ in range(steps):
        driver.execute_script("window.scrollBy(0, window.innerHeight * 0.6);")
        time.sleep(random.uniform(0.4, 0.9))

# ── Selectors — confirmed from live BizBuySell page ─────────────────────
# The page renders each listing as a <div>. We try broad selectors and
# also fall back to parsing ALL <a> tags that link to /businesses/ URLs.
CARD_SEL  = "div.featured-listing, div.organic-listing, div[class*='listing-item'], div[class*='listingResult'], section[class*='listing']"
TITLE_SEL = "h2, h3, a[class*='title'], [class*='bizName'], [class*='business-name']"
LOC_SEL   = "[class*='location'], [class*='city'], [class*='region'], [class*='metro']"
PRICE_SEL = "[class*='price'], [class*='asking'], [class*='Price']"
DESC_SEL  = "[class*='description'], [class*='snippet'], [class*='teaser'], p"

def parse_cards(soup: BeautifulSoup, state_name: str) -> list[dict]:
    cards = soup.select(CARD_SEL)

    # ── Nuclear fallback: grab every <a> that points to a BizBuySell listing ──
    # This works regardless of what wrapper div they use.
    if not cards:
        print(f"  ⚠️  CARD_SEL missed — falling back to link scrape for {state_name}")
        results = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # BizBuySell listing URLs look like /Business-Opportunity/.../ or /businesses/
            if not any(p in href for p in ["/Business-Opportunity/", "/businesses/", "/business-opportunity/"]):
                continue
            full_url = href if href.startswith("http") else "https://www.bizbuysell.com" + href

            # Walk up to find a container div with more info
            parent = a.find_parent("div") or a
            title_tag = a.find("h2") or a.find("h3") or a
            loc_tag   = parent.select_one("[class*='location'], [class*='city'], [class*='region']")
            price_tag = parent.select_one("[class*='price'], [class*='asking']")
            desc_tag  = parent.select_one("[class*='description'], [class*='snippet'], p")

            title       = title_tag.get_text(strip=True)
            location    = loc_tag.get_text(strip=True)  if loc_tag   else state_name
            price_str   = price_tag.get_text(strip=True) if price_tag else "N/A"
            description = desc_tag.get_text(strip=True)  if desc_tag  else ""

            if title and full_url not in [r["url"] for r in results]:
                results.append({
                    "title": title, "location": location,
                    "description": description, "price": price_str,
                    "url": full_url,
                })
        print(f"  Fallback found {len(results)} listings")
        return results

    if DEBUG:
        print("\nDEBUG — first card raw HTML:")
        print(cards[0].prettify()[:2000])

    results = []
    for i, card in enumerate(cards):
        title_tag = card.select_one(TITLE_SEL)
        loc_tag   = card.select_one(LOC_SEL)
        desc_tag  = card.select_one(DESC_SEL)
        price_tag = card.select_one(PRICE_SEL)
        link_tag  = card.select_one("a[href]")
        href      = card.get("href") or (link_tag["href"] if link_tag else "")

        title       = title_tag.get_text(strip=True)  if title_tag  else ""
        location    = loc_tag.get_text(strip=True)    if loc_tag    else state_name
        description = desc_tag.get_text(strip=True)   if desc_tag   else ""
        price_str   = price_tag.get_text(strip=True)  if price_tag  else "N/A"

        if DEBUG and i == 0:
            print(f"  -> title='{title}' | location='{location}' | price='{price_str}'")

        if title:
            results.append({
                "title": title, "location": location,
                "description": description, "price": price_str,
                "url": href if href.startswith("http") else "https://www.bizbuysell.com" + href,
            })
    return results


# ── Scraper ───────────────────────────────────────────────────────────────────
def scrape_bizbuysell() -> list[dict]:
    driver = make_driver()
    all_listings = []

    try:
        for state_name, url in NE_URLS.items():
            print(f"\n[BizBuySell] Scraping {state_name} → {url}")
            driver.get(url)
            _pause(2, 4)

            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, CARD_SEL))
                )
            except Exception:
                print(f"  ⚠️  Timeout waiting for listings on {state_name} — continuing anyway")

            _scroll(driver)
            _pause(1, 2)

            soup     = BeautifulSoup(driver.page_source, "html.parser")
            listings = parse_cards(soup, state_name)
            print(f"  → {len(listings)} raw listings found")
            all_listings.extend(listings)
            _pause(2, 3)

    finally:
        driver.quit()

    return all_listings

# ── Email ─────────────────────────────────────────────────────────────────────
def send_email(listings: list[dict]) -> None:
    if not APP_PASSWORD:
        print("⚠️  Set GMAIL_APP_PASSWORD env var to enable email.")
        return

    msg = MIMEMultipart()
    msg["Subject"] = f"🔥 {len(listings)} Cash-Flow Businesses — New England"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL

    body = "\n".join(
        f"Title:    {b['title']}\n"
        f"Location: {b['location']}\n"
        f"Desc:     {b['description'][:200]}\n"
        f"URL:      {b['url']}\n"
        + "-"*50
        for b in listings
    ) or "No matches found today."

    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(SENDER_EMAIL, APP_PASSWORD)
        s.send_message(msg)
    print(f"✅ Email sent — {len(listings)} listings.")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    raw = scrape_bizbuysell()

    print(f"\n{'='*60}")
    print(f"Total raw scraped: {len(raw)}\n")

    # Show every listing with filter breakdown
    print("── Filter breakdown (biz / ne / price<2M) ──")
    for b in raw:
        biz_ok   = matches_business(b["title"], b["description"])
        ne_ok    = is_new_england(b["location"])
        price_ok = is_under_2m(b.get("price", "N/A"))
        status   = f"biz={'✅' if biz_ok else '❌'}  ne={'✅' if ne_ok else '❌'}  price={'✅' if price_ok else '❌'}"
        print(f"  {status}  | {b['title'][:45]:45s} | {b['location']:20s} | {b.get('price', 'N/A')}")

    filtered = [
        b for b in raw
        if matches_business(b["title"], b["description"])
        and is_new_england(b["location"])
        and is_under_2m(b.get("price", "N/A"))
    ]

    print(f"\n✅ {len(filtered)} matches after filtering:\n")
    for b in filtered:
        print(f"  {b['title']} — {b['location']} — {b.get('price', 'N/A')}")
        print(f"    {b['url']}")

    # send_email(filtered)   # uncomment when ready