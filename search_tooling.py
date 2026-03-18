
#imports


import requests
from bs4 import BeautifulSoup

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver


NEW_ENGLAND=[state.lower() for state in ["Connecticut", "Maine", "Massachusetts", "New Hampshire", "Rhode Island", "Vermont"]]

businesses=["HVAC", "Plumbing", "Electrical", "Landscaping", "Cleaning",
    "Pest Control", "Handyman", "Lawn Care", "Snow Removal",
    "Pool Maintenance", "Roofer", "Auto mechanic", "Carpentry",
    "Painting", "Moving", "Tutoring", "Personal Training",
    "Pet Care", "Childcare", "Elderly Care", "Laundry"]


businesses=[business.lower() for business in businesses]


#find if business match the cash flow biz I am looking for

def search_businesses_title(title, description):
    text = (title + " " + description).lower()
    return any(business in text for business in businesses)


#NEW ENGLAND filter

def is_in_new_england(location):
    return any(state.lower() in location.lower() for state in NEW_ENGLAND)

#Scrape BizBuySell

def scrape_bizbuysell():
    url = "https://www.bizbuysell.com/fd/SearchResultsMulti.aspx?s_cpg=&f_seo=true"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    listings = []

    for item in soup.select(".listing"):
        title_tag = item.select_one(".title")
        location_tag = item.select_one(".location")
        description_tag = item.select_one(".desc")

        title = title_tag.text.strip() if title_tag else ""
        location = location_tag.text.strip() if location_tag else ""
        description = description_tag.text.strip() if description_tag else ""

        listings.append({
            "title": title,
            "location": location,
            "description": description
        })

    print(response.text[:500])
    print(response.status_code)

    return listings


def scrape_craigslist():
    url = "https://boston.craigslist.org/search/bfs"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    print("Status:", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    listings = []

    items = soup.find_all("li", class_="result-row")
    print("Items found:", len(items))

    for item in items:
        title_tag = item.find("a", class_="result-title")
        location_tag = item.find("span", class_="result-hood")

        title = title_tag.text.strip() if title_tag else ""
        location = location_tag.text.strip(" ()") if location_tag else "Boston"

        listings.append({
            "title": title,
            "location": location,
            "description": ""
        })

    return listings




def send_email(listings):
    sender_email = "philippe.zoghzoghi@gmail.com"
    receiver_email = "philippe.zoghzoghi@gmail.com"
    app_password = "nrkwvsshguyedfqp"  # replace this

    # Create email
    msg = MIMEMultipart()
    msg["Subject"] = "🔥 New Cash Flow Businesses Found"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    # Build email body
    body = ""

    for biz in listings:
        body += f"""
Title: {biz['title']}
Location: {biz['location']}
Description: {biz['description']}
-------------------------
"""

    if not body:
        body = "No matching businesses found today."

    msg.attach(MIMEText(body, "plain"))

    # Send email
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)

    print("✅ Email sent!")


if __name__ == "__main__":
    listings = scrape_craigslist()

    # Apply filters
    filtered = [
        biz for biz in listings
        if search_businesses_title(biz["title"], biz["description"])
        and is_in_new_england(biz["location"])
    ]

   # send_email(filtered)

    
    print(listings)
    print(f"Found {len(listings)} matching businesses in New England.")
   