import csv, time, asyncio, re

from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Path to the WebDriver executable, in this case I'm using chromedriver, this can be downloaded from the following link:
# https://developer.chrome.com/docs/chromedriver/downloads
service = Service('path/chromedriver-win64/chromedriver.exe')

# Create a new Options object
options = webdriver.ChromeOptions()

# Adding options to the Chrome driver
options.add_argument("start-maximized")  # open Browser in maximized mode
options.add_argument("disable-infobars")  # disabling infobars
options.add_argument("--disable-extensions")  # disabling extensions
options.add_argument("--no-sandbox")  # Bypass OS security model
options.add_argument('upgrade-insecure-requests=1')

# Creating the Webdriver with the options
driver = webdriver.Chrome(service=service, options=options)

def generate_booking_url(ttt, los, snapshot_date):
    """
    Generates a Booking.com search URL for the given parameters.

    Parameters:
        ttt (int): Time to Travel (days from the snapshot date).
        los (int): Length of Stay (number of nights).
        snapshot_date (datetime): The snapshot date.

    Returns:
        str: The generated Booking.com search URL.
    """
    checkin_date = snapshot_date + timedelta(days=ttt)
    checkout_date = checkin_date + timedelta(days=los)
    return f'https://www.booking.com/searchresults.html?ss=New+York&checkin_monthday={checkin_date.day}&checkin_year_month={checkin_date.strftime("%Y-%m")}&checkout_monthday={checkout_date.day}&checkout_year_month={checkout_date.strftime("%Y-%m")}&group_adults=2&no_rooms=1&lang=en-us&soz=1&lang_changed=1&selected_currency=USD'

def generate_expedia_url(ttt, los, snapshot_date):
    """
    Generate an Expedia search URL for the given parameters.

    Parameters:
        ttt (int): Time to Travel (days from the snapshot date).
        los (int): Length of Stay (number of nights).
        snapshot_date (datetime): The snapshot date.

    Returns:
        str: The generated Expedia search URL.
    """
    checkin_date = (snapshot_date + timedelta(days=ttt)).strftime('%Y-%m-%d')
    checkout_date = (snapshot_date + timedelta(days=ttt + los)).strftime('%Y-%m-%d')
    return f'https://www.expedia.com/Hotel-Search?destination=New%20York%20%28and%20vicinity%29%2C%20New%20York%2C%20United%20States%20of%20America&d1={checkin_date}&d2={checkout_date}&adults=2&rooms=1'

def scrape_booking_page(soup):
    """
    Scrape data from a Booking.com search results page.

    Parameters:
        soup (BeautifulSoup): The BeautifulSoup object of the Booking.com page.

    Returns:
        list: A list of lists containing hotel data.
    """
    data = []
    hotel_containers = soup.find_all('div', {'data-testid': 'property-card'})
    for hotel in hotel_containers:
        try:
            # Extract hotel information, this is retrieved from the html tags that appear here:
            hotel_name = hotel.find('div', {'class': 'fa4a3a8221 b121bc708f'}).get_text(strip=True)

            score_tag = hotel.find('div', {'data-testid': 'review-score'})
            score_text = score_tag.find('div', {'class': 'f13857cc8c e008572b71'}).get_text(strip=True).split()[1] if score_tag else None

            distance_tag = hotel.find('span', {'data-testid': 'distance'})
            distance = distance_tag.get_text(strip=True).split('from')[0].replace(',', '') if distance_tag else None

            if re.search(r'\bm\b', distance):
                distance = float(re.split(r'\bm\b', distance)[0]) / 1000
            elif 'km' in distance:
                distance = float(re.split(r'km', distance)[0])

            price_tag = hotel.find('span', {'data-testid': 'price-and-discounted-price'})
            price_text = price_tag.get_text(strip=True).split('$')[1].replace(',', '') if price_tag else None

            taxes_tag = hotel.find('div', {'data-testid': 'taxes-and-charges'})
            taxes_text = taxes_tag.get_text(strip=True).split('$')[1].split(' ')[0].replace(',', '') if taxes_tag else None

            total_price = float(price_text) + float(taxes_text)

            nights_adults_tag = hotel.find('div', {'data-testid': 'price-for-x-nights'})
            nights_adults_text = nights_adults_tag.get_text(strip=True) if nights_adults_tag else None

            card_deal_tag = hotel.find('span', {'data-testid': 'property-card-deal'})
            card_deal_text = card_deal_tag.get_text(strip=True) if card_deal_tag else None

            stars_tag = hotel.find('div', {'data-testid': 'rating-stars'})
            stars = len(stars_tag.find_all('svg')) if stars_tag else None

            subway_access_tag = hotel.find('span', {'class': 'f5113518a6'})
            subway_access = True if subway_access_tag else False

            neighborhood_tag = hotel.find('span', {'data-testid': 'address'})
            neighborhood = neighborhood_tag.get_text(strip=True).split(', ')[0] if neighborhood_tag else None

            room_type_tag = hotel.find('h4', {'class': 'b290e5dfa6 cf1a0708d9'})
            room_type = room_type_tag.get_text(strip=True) if room_type_tag else None

            bed_type_tag = hotel.find('div', {'class': 'ded2b5e753'}).find('div', {'class': 'b290e5dfa6'})
            bed_type = bed_type_tag.get_text(strip=True) if bed_type_tag else None

            cancellation_policy = None
            payment_policy = None

            # Find all li tags with the class 'a6a38de85e' within the hotel element
            li_tags = hotel.find_all('li', class_='deaf462b24')

            # Iterating over each li tag and extract the respective policy based on the presence of unique icons or identifiers
            for li in li_tags:
                # Checking for the cancellation policy icon
                if li.find('span', {'data-testid': 'cancellation-policy-icon'}):
                    cancellation_policy_tag = li.find('div', {'class': 'daa8593c50 a1af39b461'}).find('div', {'class': 'b290e5dfa6 b0eee6023f'})
                    cancellation_policy = cancellation_policy_tag.get_text(strip=True) if cancellation_policy_tag else None
                # Checking for the payment policy icon
                elif li.find('span', {'data-testid': 'prepayment-policy-icon'}):
                    payment_policy_tag = li.find('div', {'class': 'daa8593c50 a1af39b461'}).find('div', {'class': 'b290e5dfa6 b0eee6023f'})
                    payment_policy = payment_policy_tag.get_text(strip=True) if payment_policy_tag else None

            # Classification
            review_class_tag = hotel.find('div', {'class': 'e98ee79976 daa8593c50 fd9c2cba1d'}).find('div', {'class': 'f13857cc8c e6314e676b a287ba9834'})
            review_class = review_class_tag.get_text(strip=True) if review_class_tag else None

            number_of_reviews_tag = hotel.find('div', {'class': 'e98ee79976 daa8593c50 fd9c2cba1d'}).find('div', {'class': 'b290e5dfa6 a5cc9f664c c4b07b6aa8'})
            number_of_reviews = number_of_reviews_tag.get_text(strip=True).split('reviews')[0].replace(',', '') if number_of_reviews_tag else None

            # Append the extracted data to the data list, this is the data that will be saved to the CSV file
            data.append([
                hotel_name, score_text, distance, price_text, 
                taxes_text, total_price, nights_adults_text, card_deal_text, 
                stars, subway_access, neighborhood, room_type,
                bed_type, cancellation_policy, payment_policy, review_class, number_of_reviews
            ])
        except Exception as e:
            print(f"Encountered an exception: {e}")
            continue
    return data

async def scrape_expedia_page(url):
    """
    Scrape data from an Expedia search results page using Playwright.

    Parameters:
        url (str): The URL of the Expedia search results page.

    Returns:
        list: A list of lists containing hotel data.
    """
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url, timeout=60_000) # Increase timeout to 60 seconds, this is to ensure the page loads completely

        cards = await page.locator('[data-stid="lodging-card-responsive"]').all()
        hotels = []

        for card in cards:
            try:
                # Extracting hotel information, similar process to the Booking.com data extraction, but with playwright library
                content = card.locator('div.uitk-card-content-section')

                title = await content.locator('h3').text_content()

                price_before_tax = None
                price_before_tax_tags = content.locator('div.uitk-text.uitk-type-300.uitk-text-default-theme.is-visually-hidden')
                count = await price_before_tax_tags.count()
                for i in range(count):
                    text = await price_before_tax_tags.nth(i).text_content()
                    if 'The price' in text:
                        price_before_tax = text.split('$')[1]
                        break

                price_after_tax = None
                price_after_tax_tags = content.locator('div.uitk-text.uitk-type-end.uitk-type-200.uitk-text-default-theme')
                count = await price_after_tax_tags.count()
                for i in range(count):
                    text = await price_after_tax_tags.nth(i).text_content()
                    if 'total' in text:
                        price_after_tax = text.split('$')[1].split(' ')[0]
                        price_after_tax = price_after_tax.replace(',', '')
                        break

                rating_tag = content.locator('span.uitk-badge-base-text')
                rating = await rating_tag.text_content() if await rating_tag.is_visible() else None

                classification_tag = content.locator('span.uitk-text.uitk-type-300.uitk-type-medium.uitk-text-emphasis-theme')
                classification = await classification_tag.text_content() if await classification_tag.is_visible() else None

                reviews_tag = content.locator('span.uitk-text.uitk-type-200.uitk-type-regular.uitk-text-default-theme')
                reviews_text = await reviews_tag.text_content() if await reviews_tag.is_visible() else None
                reviews = reviews_text.replace(',', '').split()[0] if reviews_text else None

                stay_type_tag = content.locator('div.uitk-text.uitk-text-spacing-half.truncate-lines-2.uitk-type-300.uitk-text-default-theme[aria-hidden="true"]')
                stay_type = None
                bed_type = None
                if await stay_type_tag.is_visible():
                    stay_type_text = await stay_type_tag.text_content()
                    if ',' in stay_type_text:
                        stay_type, bed_type = stay_type_text.split(', ', 1)
                    else:
                        stay_type = stay_type_text

                neighborhood_tag = content.locator('div.uitk-text.uitk-text-spacing-half.truncate-lines-2.uitk-type-300.uitk-text-default-theme[aria-hidden="false"]')
                neighborhood = await neighborhood_tag.text_content() if await neighborhood_tag.is_visible() else None

                district_tag = content.locator('div.uitk-text.uitk-text-spacing-half.truncate-lines-2.uitk-type-300.uitk-text-default-theme[aria-hidden="false"]')
                district = await district_tag.text_content() if await district_tag.is_visible() else None

                cancellation_policy_tags = content.locator('div.uitk-layout-flex-item div:nth-child(1) div.uitk-text.uitk-type-300.uitk-text-positive-theme span')
                cancellation_policies = [await cancellation_policy_tags.nth(i).text_content() for i in range(await cancellation_policy_tags.count())]
                cancellation_policy = cancellation_policies[0] if cancellation_policies else None

                payment_policy_tags = content.locator('div.uitk-layout-flex-item div:nth-child(2) div.uitk-text.uitk-type-300.uitk-text-positive-theme span')
                payment_policies = [await payment_policy_tags.nth(i).text_content() for i in range(await payment_policy_tags.count())]
                payment_policy = payment_policies[0] if payment_policies else None

                # Append hotel data, this is the data that will be saved to the CSV file
                hotels.append([
                    title, price_before_tax, rating, 
                    classification, reviews, stay_type, 
                    bed_type, neighborhood, district, cancellation_policy, 
                    payment_policy, price_after_tax
                ])
            except Exception as e:
                print(f"Encountered an exception: {e}")
                continue
        await browser.close()

        return hotels

def scrape_all_pages(url, site):
    """
    Scrape all pages of search results from a given URL. REMINDER: (This will only be used in this code with the booking data).

    Parameters:
        url (str): The URL of the search results page.
        site (str): The site to scrape ('booking' or 'expedia').

    Returns:
        list: A list of lists containing all the scraped data.
    """
    driver.get(url)
    all_data = []
    while True:
        try:
            # Waiting for the property cards to be loded
            if site == 'booking':
                WebDriverWait(driver,1).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-testid="property-card"]')))
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            if site == 'booking':
                page_data = scrape_booking_page(soup)
                all_data.extend(page_data)
            # Clicking the next button to go to the next page
            next_button = None
            if site == 'booking':
                next_button = driver.find_elements(By.CSS_SELECTOR, 'button[data-testid="pagination-next"]')
            if next_button and next_button[0].is_displayed() and len(all_data) < 100:
                next_button[0].click()
                time.sleep(1)
            else:
                break
        except Exception as e:
            print(f"Encountered an exception while scraping {site}: {e}")
            break
    return all_data

def main():
    """
    Main function to scrape hotel data from Booking.com and Expedia for various search parameters.

    The data is saved to CSV files: 'booking_data.csv' and 'expedia_data.csv'.
    """
    snapshot_dates = [datetime.today(), datetime.today() + timedelta(days=7), datetime.today() + timedelta(days=14)] # Snapshot dates for the data extraction
    ttt_range = range(1, 31)    # Time to travel range
    los_range = range(1, 6)     # Length of stay range
    
    total_searches = len(snapshot_dates) * len(ttt_range) * len(los_range) # Total number of searches, this will act as a counter in the terminal
    completed_searches = 0

    all_booking_data = []
    all_expedia_data = []

    for snapshot_date in snapshot_dates:
        for ttt in ttt_range:
            for los in los_range:
                # Generating the urls for both websites
                booking_url = generate_booking_url(ttt, los, snapshot_date)
                expedia_url = generate_expedia_url(ttt, los, snapshot_date)
                
                # Scraping Booking.com data
                booking_data = scrape_all_pages(booking_url, 'booking')
                for hotel in booking_data:
                    hotel.append(snapshot_date.date())  # Added snapshot date to the data
                    hotel.append((snapshot_date + timedelta(days=ttt)).date())  # Added check-in date to the data
                    hotel.append((snapshot_date + timedelta(days=ttt + los)).date())  # Added check-out date to the data
                    hotel.append(ttt) # Added ttt to the data
                    hotel.append(los) # Added los to the data
                all_booking_data.extend(booking_data)

                # Scrapin Expedia.com data
                expedia_data = asyncio.run(scrape_expedia_page(expedia_url))
                for hotel in expedia_data:
                    hotel.append(snapshot_date.date())
                    hotel.append((snapshot_date + timedelta(days=ttt)).date())
                    hotel.append((snapshot_date + timedelta(days=ttt + los)).date())
                    hotel.append(ttt)
                    hotel.append(los)
                all_expedia_data.extend(expedia_data)
                
                completed_searches += 1
                print(f"Completed {completed_searches} out of {total_searches} searches.") # Counter

    # Saving Booking.com data to CSV, I'm ensuring here the columns that are the same with Expedia have the same name
    with open('scraped_data/booking_data1.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            "Hotel Name", "Score", "Distance to Center", "Price", 
            "Taxes and Fees", "Total Price", "Nights and Adults", "Card Deal", 
            "Stars", "Subway Access", "Neighborhood", "Room Type", "Bed Type", 
            "Cancellation Policy", "Payment Policy", "Classification", "Number of Reviews",
            "Date of search", "Checkin", "Checkout", "ttt", "los"
        ])
        writer.writerows(all_booking_data)

    # Saving Expedia data to CSV
    with open('scraped_data/expedia_data1.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Hotel Name", "Price Before Taxes", "Score", 
                        "Classification", "Number of Reviews", "Room Type", 
                        "Bed Type", "Neighborhood", "District", "Cancellation Policy", "Payment Policy",
                        "Total Price", "Date of search", "Checkin", "Checkout",
                        "ttt", "los"])
        
        writer.writerows(all_expedia_data)

    print("Data extraction completed and saved to booking_data.csv and expedia_data.csv")

if __name__ == "__main__":
    main()
    driver.quit()