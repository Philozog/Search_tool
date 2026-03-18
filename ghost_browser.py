import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import time


url = "https://example.com"
#learn how to open a browser using python and undetected chromedriver, then navigate to a website and scrape data from it.

def ghost_scraper(url)->webdriver.Chrome:
    driver=webdriver.Chrome()
    driver.get(url)
    time.sleep(10)
    
    #get headlines from the page
    headlines= driver.find_elements(By.CSS_SELECTOR, "h3 a")
    print("Found:", len(headlines), "headlines")

    for line in headlines:
        if line.text.strip():
            print(line.text)
    
    return driver

test=ghost_scraper(url)
