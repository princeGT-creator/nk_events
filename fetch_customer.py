from celery_app import app
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import json
from rentman_customer import get_customers
import time

EMAIL = "informatica@netick.it"
PASSWORD = "Netickpass13"


@app.task(name='scrape_customer_data_task')
def scrape_customer_data_task():

    # Set up Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Enable headless mode
    options.add_argument("--headless")  # Runs Chrome in headless mode
    options.add_argument("--disable-gpu")  # Applicable to Windows
    options.add_argument("--window-size=1920,1080")  # Optional but recommended for consistent rendering
    options.add_argument("--no-sandbox")  # Optional, useful for some environments
    options.add_argument("--disable-dev-shm-usage")  # Helps with memory issues on Linux

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    def scrape_billing_address(customer_id):
        details_url = f"https://netick.rentmanapp.com/#/contacts/{customer_id}/details"
        driver.get(details_url)

        time.sleep(3)  # Give time for the page to load

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "rm-contact-address-card__body-content"))
            )
            print(f"✅ Billing address section loaded for customer {customer_id}")

            address = {}

            def get_input_value(data_qa):
                try:
                    input_element = driver.find_element(By.CSS_SELECTOR, f"input[data-qa='{data_qa}__text-input']")
                    return input_element.get_attribute("value").strip()
                except Exception as e:
                    print(f"⚠️ Couldn't find field {data_qa}: {e}")
                    return ""

            def get_country_value():
                try:
                    country_span = driver.find_element(
                        By.CSS_SELECTOR,
                        "button[data-qa='contact-edit__details__invoice-address__input-factuurland__open-select'] span.rm-select__label"
                    )
                    return country_span.text.strip()
                except Exception as e:
                    print(f"⚠️ Couldn't find country field: {e}")
                    return ""

            address["street"] = get_input_value("contact-edit__details__invoice-address__input-factuurstraat")
            address["street_number"] = get_input_value("contact-edit__details__invoice-address__input-factuurhuisnummer")
            address["postal_code"] = get_input_value("contact-edit__details__invoice-address__input-factuurpostcode")
            address["city"] = get_input_value("contact-edit__details__invoice-address__input-factuurstad")
            address["province"] = get_input_value("contact-edit__details__invoice-address__input-factuurprovincie")
            address["country"] = get_country_value()

            print(f"📦 Extracted billing address for {customer_id}: {address}")
            return address

        except Exception as e:
            print(f"❌ Failed to fetch billing address for {customer_id}: {e}")
            return {}

    def scrape_digital_invoicing(customer_id):
        invoicing_url = f"https://netick.rentmanapp.com/#/contacts/{customer_id}/digital-invoicing"
        driver.get(invoicing_url)

        time.sleep(3)  # Let the page load

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "rm-form-grid"))
            )
            print(f"✅ Digital invoicing section loaded for customer {customer_id}")

            def get_input(data_qa):
                try:
                    input_elem = driver.find_element(By.CSS_SELECTOR, f"input[data-qa='{data_qa}__text-input']")
                    return input_elem.get_attribute("value").strip()
                except Exception as e:
                    print(f"⚠️ Could not find field {data_qa}: {e}")
                    return ""

            invoicing_info = {
                "e_invoice_id": get_input("contact-edit__digital-invoicing__input-e_invoice_id"),
                "e_invoice_id_type": get_input("contact-edit__digital-invoicing__input-e_invoice_id_type"),
                "pec_email": get_input("contact-edit__digital-invoicing__input-e_invoice_pa_email"),
                "recipient_code": get_input("contact-edit__digital-invoicing__input-e_invoice_pa_code")
            }

            print(f"📩 Extracted invoicing details for {customer_id}: {invoicing_info}")
            return invoicing_info

        except Exception as e:
            print(f"❌ Failed to fetch digital invoicing data for {customer_id}: {e}")
            return {}
        

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


    driver.get("https://rentman.io")

    # Click the menu button (if needed)
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

        # Wait for the organization selection page to load
        org_card = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "account-card"))
        )
        print("✅ Organization selection page loaded.")

        # Hover over the organization card
        actions = ActionChains(driver)
        actions.move_to_element(org_card).perform()
        print("✅ Hovered over the organization card.")

        # Click the "Accedi" button
        accedi_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@class='account-loginbutton']/button"))
        )
        accedi_button.click()
        print("✅ 'Accedi' button clicked! Navigating to the organization dashboard...")

        print("⏳ Waiting for the dashboard to fully load before scraping...")
        time.sleep(12)
        
        customers = get_customers()
        results = []

        for customer in customers:
            customer_id = customer["id"]
            customer_name = customer["name"]
            vat_number = customer['vat_number']

            print(f"🔍 Processing customer: {customer_name} (ID: {customer_id})")
            
            # Scrape billing date and payment term
            # billing_date = scrape_billing_date(customer_id)
            # payment_term = scrape_payment_terms(customer_id)
            address = scrape_billing_address(customer_id)
            digital_invoicing = scrape_digital_invoicing(customer_id)

            # Store in results list
            results.append({
                "id": customer_id,
                "name": customer_name,
                "vat_number": vat_number,
                "address": address,
                "digital_invoicing": digital_invoicing
                # "billing_date": billing_date,
                # "payment_term": payment_term
            })
            print('results: ', results)

        # Save results to JSON file
        with open("customer_details.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

        print("✅ Data scraping complete! Results saved to 'customer_details.json'.")
        return

    else:
        print("❌ Login URL not found!")

# scrape_customer_data_task.delay()