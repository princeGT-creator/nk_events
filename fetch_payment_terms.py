import time
import json
from celery_app import app
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

from rentman_customer import get_customers
import logging



# Rentman API Token (Replace with your actual token)
# Your Rentman credentials (replace with your actual credentials)
EMAIL = "informatica@netick.it"
PASSWORD = "Netickpass13"


@app.task(name='scrape_customer_payment_terms')
def scrape_customer_payment_terms():
    TARGET_ORGANIZATION = "Nk Events"
    # Set up logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Add handler to logger
    if not logger.hasHandlers():  # Prevent duplicate handlers on reloads
        logger.addHandler(console_handler)

    # Set up Selenium WebDriver
    options = Options()

    # Chrome headless and stability options
    options.add_argument('--headless=new')  # Use the new headless mode
    options.add_argument('--no-sandbox')   # Needed in many containerized or restricted envs
    options.add_argument('--disable-dev-shm-usage')  # Avoid /dev/shm issues
    options.add_argument('--disable-gpu')   # Disable GPU acceleration
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--remote-debugging-port=9222')  # Optional remote debugging

    # Privacy and cache options
    options.add_argument('--incognito')
    options.add_argument('--disable-application-cache')
    options.add_argument('--enable-do-not-track')
    options.add_argument('--disable-popup-blocking')

    # Explicit binary location
    options.binary_location = '/usr/bin/chromium-browser'

    # Path to chromedriver executable
    service = Service('/usr/bin/chromedriver')

    # Initialize WebDriver
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Set up logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(console_handler)

        def scrape_billing_date(customer_id):
            billing_url = f"https://netick.rentmanapp.com/#/contacts/{customer_id}/payments"
            driver.get(billing_url)

            # Ensure the page loads fully
            time.sleep(3)  # Small delay to allow full rendering

            try:
                # Wait for the section containing payment details
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//rm-label-input[@columnid='factuurmoment']"))
                )
                print(f"✅ Payment page loaded for customer {customer_id}")

                # Locate the dropdown button inside 'factuurmoment' section
                dropdown_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//rm-label-input[@columnid='factuurmoment']//button[@class='form-control rm-select__toggle-button rm-dropdown-toggle']"))
                )

                # Extract the Billing date value from the span inside the button
                billing_date = dropdown_button.find_element(By.CLASS_NAME, "rm-select__label").text.strip()

                print(f"🎯 Extracted Billing date: {billing_date}")
                return billing_date
            except Exception as e:
                print(f"⚠️ Error fetching Billing date for {customer_id}: {e}")
                return None

        def scrape_payment_terms(customer_id):
            billing_url = f"https://netick.rentmanapp.com/#/contacts/{customer_id}/payments"
            driver.get(billing_url)
            
            # Ensure the page loads fully
            time.sleep(3)
            
            try:
                # Wait for the payment terms dropdown to be present
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//rm-label-input[@columnid='betalingsconditie']"))
                )
                print(f"✅ Payment page loaded for customer {customer_id}")
                
                # Locate the dropdown button inside 'betalingsconditie' section
                dropdown_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//rm-label-input[@columnid='betalingsconditie']//button[@class='form-control rm-select__toggle-button rm-dropdown-toggle']"))
                )
                
                # Extract the payment terms value from the span inside the button
                payment_terms = dropdown_button.find_element(By.CLASS_NAME, "rm-select__label").text.strip()
                
                print(f"🎯 Extracted Payment Terms: {payment_terms}")
                return payment_terms
            except Exception as e:
                print(f"⚠️ Error fetching Payment Terms for {customer_id}: {e}")
                return None

        def ensure_logged_in():
            try:
                WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, "account-card")))
                print("⚠️ Re-authenticating...")
                org_cards = driver.find_elements(By.CLASS_NAME, "account-card")
                for card in org_cards:
                    org_name = card.find_element(By.TAG_NAME, "h5").text.strip()
                    if org_name == TARGET_ORGANIZATION:
                        ActionChains(driver).move_to_element(card).perform()
                        card.find_element(By.XPATH, ".//div[@class='account-loginbutton']/button").click()
                        time.sleep(10)
                        return
            except TimeoutException:
                pass
        # Click the menu button (if needed)
        # Open Rentman homepage
        driver.get("https://rentman.io")
        logger.info("Opened Rentman homepage.")

        try:
            menu_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "c-overlay-menu__toggle"))
            )
            menu_button.click()
            print("✅ Menu button clicked!")
        except Exception:
            print("⚠️ No menu button found, skipping...")

        # Find the Login button and extract its URL
        try:
            login_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.LINK_TEXT, "Login"))
            )
            login_url = login_button.get_attribute("href")
        except Exception:
            print("❌ Could not find Login button!")
            login_url = None

        if login_url:
            print(f"🔗 Extracted Login URL: {login_url}")
            driver.get(login_url)
            WebDriverWait(driver, 10).until(EC.url_contains("rentmanapp.com/login"))
            print("✅ Successfully navigated to:", driver.current_url)

            # Wait for email and password fields
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            password_input = driver.find_element(By.ID, "password")

            # Enter login credentials
            email_input.send_keys(EMAIL)
            password_input.send_keys(PASSWORD)
            print("✅ Entered email and password.")

            # Click the login button
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            print("✅ Login button clicked!")

            # # Wait for the organization selection page to load
            # org_card = WebDriverWait(driver, 10).until(
            #     EC.presence_of_element_located((By.CLASS_NAME, "account-card"))
            # )
            # print("✅ Organization selection page loaded.")

            # # Hover over the organization card
            # actions = ActionChains(driver)
            # actions.move_to_element(org_card).perform()
            # print("✅ Hovered over the organization card.")

            # # Click the "Accedi" button
            # accedi_button = WebDriverWait(driver, 10).until(
            #     EC.element_to_be_clickable((By.XPATH, "//div[@class='account-loginbutton']/button"))
            # )
            # accedi_button.click()
            # print("✅ 'Accedi' button clicked! Navigating to the organization dashboard...")

            print("⏳ Waiting for the dashboard to fully load before scraping...")
            time.sleep(12)
            
            customers = get_customers()
            results = []

            for customer in customers:
                customer_id = customer["id"]
                customer_name = customer["name"]

                logger.info(f"🔍 Processing customer: {customer_name} (ID: {customer_id})")
                
                # Scrape billing date and payment term
                ensure_logged_in()
                billing_date = scrape_billing_date(customer_id)
                payment_term = scrape_payment_terms(customer_id)

                # billing_date, payment_term = scrape_payment_terms(customer_id)

                # Store in results list
                results.append({
                    "id": customer_id,
                    "name": customer_name,
                    "billing_date": billing_date,
                    "payment_term": payment_term
                })
                logger.info('results: ', results)

            # Save results to JSON file
            with open("customer_payment_terms.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)

            logger.info("✅ Data scraping complete! Results saved to 'customer_payment_terms.json'.")
            # Close the browser
            driver.quit()
            return

        else:
            logger.error("❌ Login URL not found!")
    finally:
        driver.quit()
# scrape_customer_payment_terms.delay()