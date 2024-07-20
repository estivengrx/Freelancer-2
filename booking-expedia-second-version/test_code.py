import csv
import time
import asyncio
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Path to the WebDriver executable
service = Service('D:/Estiven/Trabajo/Freelancer 2/booking-expedia-second-version/chromedriver-win64/chromedriver.exe')

# Create a new Options object
options = Options()
options.add_argument("start-maximized")
options.add_argument("disable-infobars")
options.add_argument("--disable-extensions")
options.add_argument("--no-sandbox")
options.add_argument('upgrade-insecure-requests=1')

# Create the WebDriver with the options
driver = webdriver.Chrome(service=service, options=options)

def generate_booking_url(ttt, los, snapshot_date):
    checkin_date = snapshot_date + timedelta(days=ttt)
    checkout_date = checkin_date + timedelta(days=los)
    return f'https://www.booking.com/searchresults.html?ss=New+York&checkin_monthday={checkin_date.day}&checkin_year_month={checkin_date.strftime("%Y-%m")}&checkout_monthday={checkout_date.day}&checkout_year_month={checkout_date.strftime("%Y-%m")}&group_adults=2&no_rooms=1&lang=en-us&soz=1&lang_changed=1&selected_currency=USD'

def generate_expedia_url(ttt, los, snapshot_date):
    checkin_date = (snapshot_date + timedelta(days=ttt)).strftime('%Y-%m-%d')
    checkout_date = (snapshot_date + timedelta(days=ttt + los)).strftime('%Y-%m-%d')
    return f'https://www.expedia.com/Hotel-Search?destination=New%20York%20%28and%20vicinity%29%2C%20New%20York%2C%20United%20States%20of%20America&d1={checkin_date}&d2={checkout_date}&adults=2&rooms=1'

def scrape_booking_page(soup, ttt, los, date_of_search):
    data = []
    hotel_containers = soup.find_all('div', {'data-testid': 'property-card'})
    for index, hotel in enumerate(hotel_containers):
        try:
            hotel_name_tag = hotel.find('div', {'class': 'e037993315 f5f8fe25fa'})
            hotel_name = hotel_name_tag.get_text(strip=True) if hotel_name_tag else 'N/A'
            score_tag = hotel.find('div', {'data-testid': 'review-score'})
            score_text = score_tag.find('div', {'class': 'a447b19dfd'}).get_text(strip=True).split()[1] if score_tag else 'N/A'
            distance_tag = hotel.find('span', {'data-testid': 'distance'})
            distance_text = distance_tag.get_text(strip=True).split('from')[0].replace(',', '') if distance_tag else 'N/A'
            distance = None
            if re.search(r'\bm\b', distance_text):
                distance = float(re.split(r'\bm\b', distance_text)[0]) / 1000
            elif 'km' in distance_text:
                distance = float(re.split(r'km', distance_text)[0])

            price_tag = hotel.find('span', {'data-testid': 'price-and-discounted-price'})
            price_text = price_tag.get_text(strip=True).split('$')[1].replace(',', '') if price_tag else 'N/A'
            taxes_tag = hotel.find('div', {'data-testid': 'taxes-and-charges'})
            taxes_text = taxes_tag.get_text(strip=True).split('$')[1].split(' ')[0].replace(',', '') if taxes_tag else 'N/A'
            total_price = float(price_text) + float(taxes_text) if price_text != 'N/A' and taxes_text != 'N/A' else 'N/A'

            nights_adults_tag = hotel.find('div', {'data-testid': 'price-for-x-nights'})
            nights_adults_text = nights_adults_tag.get_text(strip=True) if nights_adults_tag else 'N/A'
            stars_tag = hotel.find('div', {'data-testid': 'rating-stars'})
            stars = len(stars_tag.find_all('svg')) if stars_tag else 'N/A'
            subway_access_tag = hotel.find('span', {'class': 'cdebd92b49'})
            subway_access = True if subway_access_tag else False
            neighborhood_tag = hotel.find('span', {'data-testid': 'address'})
            neighborhood = neighborhood_tag.get_text(strip=True).split(', ')[0] if neighborhood_tag else 'N/A'
            room_type_tag = hotel.find('h4', {'class': 'e8acaa0d22 e7baf22fe8'})
            room_type = room_type_tag.get_text(strip=True) if room_type_tag else 'N/A'
            bed_type_tag = hotel.find('div', {'class': 'dfdb404493'}).find('div', {'class': 'e8acaa0d22'})
            bed_type = bed_type_tag.get_text(strip=True) if bed_type_tag else 'N/A'

            cancellation_policy = None
            payment_policy = None
            li_tags = hotel.find_all('ul', class_='cf8b8c08b2')

            for li in li_tags:
                if li.find('span', {'data-testid': 'cancellation-policy-icon'}):
                    cancellation_policy_tag = li.find('div', {'class': 'ec7ca45eb7 c5df7d7c0e'}).find('div', {'class': 'e8acaa0d22 d40b1dc96f'})
                    cancellation_policy = cancellation_policy_tag.get_text(strip=True) if cancellation_policy_tag else 'N/A'
                elif li.find('span', {'data-testid': 'prepayment-policy-icon'}):
                    payment_policy_tag = li.find('div', {'class': 'ec7ca45eb7 c5df7d7c0e'}).find('div', {'class': 'e8acaa0d22 d40b1dc96f'})
                    payment_policy = payment_policy_tag.get_text(strip=True) if payment_policy_tag else 'N/A'

            review_class_tag = hotel.find('div', {'data-testid': 'review-score'}).find('div', {'class': 'd0522b0cca eb02592978 f374b67e8c'})
            review_class = review_class_tag.get_text(strip=True) if review_class_tag else 'N/A'
            number_of_reviews_tag = hotel.find('div', {'data-testid': 'review-score'}).find('div', {'class': 'e8acaa0d22 ab107395cb c60bada9e4'})
            number_of_reviews = number_of_reviews_tag.get_text(strip=True).split('reviews')[0].replace(',', '') if number_of_reviews_tag else 'N/A'

            data.append([
                ttt, los, date_of_search, index, hotel_name, score_text, distance, price_text, taxes_text, total_price,
                nights_adults_text, stars, subway_access, neighborhood, room_type, bed_type, cancellation_policy,
                payment_policy, review_class, number_of_reviews
            ])
        except Exception as e:
            print(f"Encountered an exception at index {index}: {e}")
            continue
    return data

async def scrape_expedia_page(url, ttt, los, date_of_search):
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url, timeout=60_000)

        cards = await page.locator('[data-stid="lodging-card-responsive"]').all()
        hotels = []
        for index, card in enumerate(cards):
            try:
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
                        price_after_tax = text.split('$')[1].split(' ')[0].replace(',', '')
                        break

                rating_tag = content.locator('span.uitk-badge-base-text')
                rating = await rating_tag.text_content() if await rating_tag.is_visible() else 'N/A'
                classification_tag = content.locator('span.uitk-text.uitk-type-300.uitk-type-medium.uitk-text-emphasis-theme')
                classification = await classification_tag.text_content() if await classification_tag.is_visible() else 'N/A'
                reviews_tag = content.locator('span.uitk-text.uitk-type-200.uitk-type-regular.uitk-text-default-theme')
                reviews_text = await reviews_tag.text_content() if await reviews_tag.is_visible() else 'N/A'
                reviews = reviews_text.replace(',', '').split()[0] if reviews_text else 'N/A'
                neighborhood_tag = content.locator('div.uitk-text.uitk-text-spacing-half.truncate-lines-2.uitk-type-300.uitk-text-default-theme[aria-hidden="false"]')
                neighborhood = await neighborhood_tag.text_content() if await neighborhood_tag.is_visible() else 'N/A'

                hotels.append([
                    ttt, los, date_of_search, index, title, price_before_tax, price_after_tax, rating, classification,
                    reviews, neighborhood
                ])
            except Exception as e:
                print(f"Encountered an exception at index {index}: {e}")
                continue
        await browser.close()
        return hotels

async def main():
    snapshot_date = datetime.today().strftime('%Y-%m-%d')
    booking_data = []
    expedia_data = []

    for ttt in range(1, 3):
        for los in range(1, 2):
            booking_url = generate_booking_url(ttt, los, datetime.strptime(snapshot_date, '%Y-%m-%d'))
            expedia_url = generate_expedia_url(ttt, los, datetime.strptime(snapshot_date, '%Y-%m-%d'))

            driver.get(booking_url)
            time.sleep(10)
            booking_soup = BeautifulSoup(driver.page_source, 'html.parser')
            booking_data.extend(scrape_booking_page(booking_soup, ttt, los, snapshot_date))

            expedia_data.extend(await scrape_expedia_page(expedia_url, ttt, los, snapshot_date))
            print(f'Finished scraping for TTT={ttt} and LOS={los}')

    driver.quit()

    with open('booking_results.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['TTT', 'LOS', 'Date of Search', 'Index', 'Hotel Name', 'Score', 'Distance', 'Price Before Tax', 'Taxes', 'Total Price', 
                         'Nights & Adults', 'Stars', 'Subway Access', 'Neighborhood', 'Room Type', 'Bed Type', 'Cancellation Policy', 
                         'Payment Policy', 'Review Class', 'Number of Reviews'])
        writer.writerows(booking_data)

    with open('expedia_results.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['TTT', 'LOS', 'Date of Search', 'Index', 'Hotel Name', 'Price Before Tax', 'Price After Tax', 'Rating', 
                         'Classification', 'Reviews', 'Neighborhood'])
        writer.writerows(expedia_data)

# Run the main function
asyncio.run(main())