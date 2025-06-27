import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import re

# Function to initialize the WebDriver
def init_driver():
    ua = UserAgent()
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-agent={ua.random}")  # Random user-agent
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")  # Run in headless mode (optional)

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Function to wait for an element to load
def wait_for_element(driver, by, selector, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
    except:
        return None

# Function to clean price (convert ₹1,299 to 1299)
def clean_price(price):
    if price == "N/A":
        return None
    return int(re.sub(r"[^\d]", "", price))

# Function to scrape Amazon
def scrape_amazon(driver, search_item):
    url = f"https://www.amazon.in/s?k={search_item.replace(' ', '+')}"
    driver.get(url)
    
    wait_for_element(driver, By.CSS_SELECTOR, '[data-component-type="s-search-result"]')

    script = """
    let product = document.querySelectorAll('[data-component-type="s-search-result"]')[0]; 
    if (!product) return {'price': 'N/A', 'reviews': 'N/A'};

    let priceElement = product.querySelector('.a-price-whole');
    let reviewElement = product.querySelector('.a-row.a-size-small span');

    let price = priceElement ? priceElement.innerText : 'N/A';
    let reviews = reviewElement ? reviewElement.innerText : 'N/A';

    return {'price': price, 'reviews': reviews};
    """
    result = driver.execute_script(script)
    return {"Website": "Amazon", "Price": result['price'], "Reviews": result['reviews']}

# Function to scrape Flipkart
def scrape_flipkart(driver, search_item):
    url = f"https://www.flipkart.com/search?q={search_item.replace(' ', '%20')}"
    driver.get(url)

    wait_for_element(driver, By.XPATH, '(//div[contains(@class, "_1AtVbE")])[2]')

    try:
        price_xpaths = [
            '(//div[contains(@class, "_30jeq3")])[1]',  # Old structure
            '(//div[contains(@class, "Nx9bqj")])[1]',  # New structure
            '//*[contains(text(), "₹")][1]'  # Any price with ₹ symbol
        ]

        price = "N/A"
        for xpath in price_xpaths:
            try:
                price_element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
                price = price_element.text if price_element else "N/A"
                if price != "N/A":
                    break
            except:
                continue

        reviews_xpath = '(//span[contains(@class, "_2_R_DZ")])[1]'
        try:
            reviews_element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, reviews_xpath)))
            reviews = reviews_element.text if reviews_element else "N/A"
        except:
            reviews = "N/A"

    except Exception as e:
        print(f"Flipkart Scraper Error: {e}")
        return {"Website": "Flipkart", "Price": "N/A", "Reviews": "N/A"}

    return {"Website": "Flipkart", "Price": price, "Reviews": reviews}

# Function to scrape Myntra
def scrape_myntra(driver, search_item):
    url = f"https://www.myntra.com/{search_item.replace(' ', '-')}"
    driver.get(url)

    wait_for_element(driver, By.XPATH, '(//li[contains(@class, "product-base")])[1]')

    try:
        price_element = driver.find_element(By.XPATH, '(//span[contains(@class, "product-discountedPrice")])[1]')
        rating_element = driver.find_element(By.XPATH, '(//div[contains(@class, "product-ratingsContainer")])[1]')

        price = price_element.text if price_element else "N/A"
        reviews = rating_element.text if rating_element else "N/A"

    except Exception as e:
        print(f"Myntra Scraper Error: {e}")
        return {"Website": "Myntra", "Price": "N/A", "Reviews": "N/A"}

    return {"Website": "Myntra", "Price": price, "Reviews": reviews}

# Function to find the website with the lowest price above average
def find_lowest_price(df):
    df["Cleaned_Price"] = df["Price"].apply(lambda x: int(re.sub(r"[^\d]", "", x)) if re.search(r"\d", x) else 0)
    df.fillna(0, inplace=True)
    valid_prices = df[df["Cleaned_Price"] > 0]
    if valid_prices.empty:
        return "No valid prices found."
    best_deal = valid_prices.loc[valid_prices["Cleaned_Price"].idxmin()]
    return f"Website with the lowest price: {best_deal['Website']} - ₹{best_deal['Cleaned_Price']}"

# Streamlit UI
st.title("E-Commerce Price Comparison")
search_item = st.text_input("Enter the product name to search:")

if st.button("Search"):
    st.write("Fetching data, please wait...")
    driver = init_driver()
    results = []
    results.append(scrape_amazon(driver, search_item))
    results.append(scrape_flipkart(driver, search_item))
    results.append(scrape_myntra(driver, search_item))
    driver.quit()
    df = pd.DataFrame(results)
    df.to_csv("file.csv", index=False)
    st.write("### Scraped Data")
    st.dataframe(df)
    best_deal = find_lowest_price(df)
    st.write("### Best Deal")
    st.success(best_deal)
