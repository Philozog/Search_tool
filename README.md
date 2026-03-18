Your README is already strong — this is a **cleaned, sharper, more professional version** (tightened language, clearer structure, more “GitHub-ready” and credible for recruiters 👇)

---

# 🔍 BizBuySell New England Cash-Flow Scraper

A Python-based scraper that automatically extracts **cash-flowing, service-based businesses** listed on BizBuySell across the six New England states.

Designed for **deal sourcing, search fund research, and acquisition screening**.

---

## 🚀 Features

* 🌎 Scrapes all 6 New England states:

  * Massachusetts, Connecticut, Maine, New Hampshire, Rhode Island, Vermont
* 🧠 Filters for **service-based, cash-flow businesses**:

  * HVAC, plumbing, roofing, cleaning, landscaping, etc.
* 💰 Filters listings with **asking price < $2,000,000**
* 🛡️ Bypasses Cloudflare bot detection using a real Chrome browser
* 🔎 Displays a **transparent filter breakdown** (why each listing passed/failed)
* 📩 Optional **daily email alerts** via Gmail

---

## 🧰 Tech Stack

* Python 3.10+
* Selenium
* undetected-chromedriver
* BeautifulSoup

Install dependencies:

```bash
pip install undetected-chromedriver selenium beautifulsoup4
```

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/bizbuysell-scraper.git
cd bizbuysell-scraper
```

---

_### 2. Configure environment variables (email alerts)

⚠️ Credentials are **never hardcoded** — they are loaded via environment variables.

#### Windows (PowerShell)

```powershell
$env:GMAIL_APP_PASSWORD = "your_app_password"
$env:SENDER_EMAIL       = "you@gmail.com"
$env:RECEIVER_EMAIL     = "you@gmail.com"
```

#### Mac / Linux

```bash
export GMAIL_APP_PASSWORD="your_app_password"
export SENDER_EMAIL="you@gmail.com"
export RECEIVER_EMAIL="you@gmail.com"
```

👉 To generate a Gmail App Password:
Google Account → Security → 2-Step Verification → App Passwords → "Mail"_

---

## ▶️ Usage

### Run the scraper

```bash
python scraper.py
```

A Chrome browser will launch and automatically scrape listings.

Example output:

```
── Filter breakdown (biz / ne / price<2M) ──
biz=✅  ne=✅  price=✅  | Plumbing Company         | Boston, MA   | $850,000
biz=✅  ne=✅  price=❌  | Electrical Contractor    | Hartford, CT | $3,200,000
biz=❌  ne=✅  price=✅  | Restaurant (Absentee)    | Providence   | $295,000

✅ 12 matches:
Plumbing Company — Boston, MA — $850,000
https://www.bizbuysell.com/...
```

---

### 📩 Enable email alerts (UNDER COMSTRUCTION STILL)

Uncomment this line in `scraper.py`:

```python
send_email(filtered)
```

---

### 🧪 Run headless (no browser UI)

```python
opts.add_argument("--headless=new")
```

---

## 🔍 Filtering Logic

All three conditions must be met:

| Filter        | Description                           |
| ------------- | ------------------------------------- |
| Business Type | Matches keywords in `BUSINESSES` list |
| Geography     | Located in New England                |
| Price         | Below $2,000,000 (or missing price)   |

---

### 🛠️ Customize business types

Edit the keyword list:

```python
BUSINESSES = [
    "hvac", "plumbing", "roofing", "cleaning",
    "landscaping", "electrical", "laundry",
]
```

---

### 💰 Adjust price threshold

```python
def is_under_2m(price_str: str) -> bool:
    price = parse_price(price_str)
    return price == 0 or price < 2_000_000
```

---

## ⏱️ Scheduling (Daily Automation)

### Windows — Task Scheduler

1. Create Basic Task
2. Trigger: Daily
3. Action:

```bash
python C:\path\to\scraper.py
```

---

### Mac / Linux — cron

```bash
crontab -e
```

Add:

```bash
0 8 * * * /usr/bin/python3 /path/to/scraper.py
```

---

## 📁 Project Structure

```
bizbuysell-scraper/
├── scraper.py
└── README.md
```

---

## 🧯 Troubleshooting

### ❌ No listings returned

* Ensure `DEBUG = True`
* Check for:

  ```
  ⚠️ CARD_SEL missed
  ```
* If triggered, update selectors in `scraper.py`

---

### ⚠️ Chrome version mismatch

* Update Chrome to latest version
* `undetected-chromedriver` should auto-sync

---

### 🔐 Gmail authentication error

* Use **App Password**, not your main password

---

### 🧱 HTML structure changed

* Enable debug mode
* Inspect output:

  ```
  DEBUG — first card raw HTML
  ```
* Update selectors:

  * `CARD_SEL`
  * `TITLE_SEL`
  * `LOC_SEL`
  * `PRICE_SEL`

---

## ⚠️ Disclaimer

This project is for **personal research and educational purposes only**.

Please review BizBuySell Terms of Service before using this tool. The scraper uses delays and a real browser to minimize server load.





