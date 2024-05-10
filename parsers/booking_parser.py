import time
import logging
import sys
import random
from urllib.parse import quote_plus
from typing import Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException, SessionNotCreatedException, ElementNotInteractableException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from utils.constants import LOAD_MORE_BUTTON_CLICKS


# Configure basic logging to output to standard system output
logging.basicConfig(level=logging.INFO, stream=sys.stdout)


# Function to parse hotel booking information
def parse_booking(
    destination: str, check_in: str, check_out: str, adults: int,
    rooms: int, children: int, children_age: list[Optional[int]], order_by: str
) -> Optional[list[dict]]:
    # Generate the URL for the booking site with the given parameters
    url = create_url(destination, check_in, check_out, adults, rooms, children, children_age, order_by)

    # Set up options for the Selenium WebDriver
    options = Options()
    # Add incognito mode
    options.add_argument('--incognito')
    # Run Chrome in headless mode
    options.add_argument("--headless=new")
    # Set the window size
    options.add_argument('--window-size=1920,1080')
    options.add_argument("--start-maximized")
    # Set a user agent to mimic a real browser visit
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/123.0.0.0 Safari/537.36'
    )

    # Initialize the WebDriver and navigate to the URL
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url=url)
    # Exit if the session could not be created
    except SessionNotCreatedException:
        return

    # Initialize variables for scrolling and loading more results
    exit_check = 0
    load_more_button_counter = 0

    # Scroll the page and attempt to load more results
    while load_more_button_counter < LOAD_MORE_BUTTON_CLICKS and exit_check < 6:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # Scroll up a random number of pixels to simulate user behavior
        scroll_up_pixels = random.randint(465, 565)
        driver.execute_script(f"window.scrollBy(0, -{scroll_up_pixels});")

        # Attempt to avoid add
        try:
            driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss sign-in info.']").click()
        except NoSuchElementException:
            pass

        # Attempt to reject cookies
        try:
            driver.find_element(By.ID, 'onetrust-reject-all-handler').click()
            time.sleep(1)
        except (NoSuchElementException, ElementNotInteractableException):
            pass

        # Attempt to find and click the 'Load more results' button
        try:
            load_more_button = WebDriverWait(driver, random.uniform(1, 1.25)).until(
                EC.presence_of_element_located((By.XPATH, "//span[text()='Load more results']"))
            )
            # Click the button to load more results
            load_more_button.click()
            # Increment the counter
            load_more_button_counter += 1
            # Wait for the results to load
            time.sleep(random.uniform(1, 1.25))
            # Reset the exit check counter
            exit_check = 0
        except TimeoutException:
            # Increment the exit check counter if the button is not found
            exit_check += 1
            pass

    # Pause to ensure all data has loaded
    time.sleep(random.uniform(1.75, 2))
    # Retrieve the page source and quit the WebDriver
    page_source = driver.page_source
    driver.quit()
    # Parse the page source with BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')
    # Select all property cards from the page
    properties = soup.select('div[data-testid="property-card"]')

    # Initialize a list to store information about each property
    info = []
    # Iterate over each property card and extract information
    for single_property in properties:
        name = single_property.select_one('div[data-testid="title"]').text
        price_element = single_property.select_one('span[data-testid="price-and-discounted-price"]').text
        price = int(price_element.split('$')[1].replace(',', ''))
        photo = single_property.select_one('img')['src']
        link = single_property.select_one('a')['href']
        rating_element = single_property.select_one('div[data-testid="review-score"]')

        if rating_element:
            rating = float(rating_element.text.split()[1])
        else:
            rating = None

        # Store the extracted information in a dictionary
        single_info = {
            'Name': name,
            'Price': price,
            'Rating': rating,
            'Photo': photo,
            'Link': link
        }
        # Add the dictionary to the list
        info.append(single_info)

    # Return the list of property information
    return info


# Function to create a URL with the specified search parameters
def create_url(
    destination: str, check_in: str, check_out: str, adults: int,
    rooms: int, children: int, children_age: list[Optional[int]], order_by: str
) -> str:
    # Base URL for the search
    base_url = 'https://www.booking.com/searchresults.html'
    # URL-encode the destination
    destination = quote_plus(destination)

    # Construct the query parameters for the URL
    params = (
        f'ss={destination}&'
        'lang=en-us&'
        'selected_currency=USD&'
        f'checkin={check_in}&'
        f'checkout={check_out}&'
        f'group_adults={adults}&'
        f'no_rooms={rooms}&'
        f'order={order_by}&'
        f'group_children={children}'
    )

    # Add parameters for children's ages if children are included in the search
    if children > 0:
        age_params = '&'.join(f'age={age}' for age in children_age)
        params = f'{params}&{age_params}'

    # Combine the base URL with the query parameters
    url = f'{base_url}?{params}'
    # Return the constructed URL
    return url
