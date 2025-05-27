from celery_app import app
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import json
from rentman_customer import get_customers
import time
from selenium.common.exceptions import TimeoutException

EMAIL = "informatica@netick.it"
PASSWORD = "Netickpass13"


@app.task(name='scrape_customer_data_task')
def scrape_customer_data_task():
    TARGET_ORGANIZATION = "Nk Events"

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

            # # ✅ Now wait and select the right organization
            # WebDriverWait(driver, 10).until(
            #     EC.presence_of_all_elements_located((By.CLASS_NAME, "account-card"))
            # )
            # org_cards = driver.find_elements(By.CLASS_NAME, "account-card")

            # target_found = False
            # for card in org_cards:
            #     try:
            #         title_elem = card.find_element(By.TAG_NAME, "h5")
            #         org_name = title_elem.text.strip()
            #         if org_name == TARGET_ORGANIZATION:
            #             print(f"✅ Found target organization: {org_name}")
            #             actions = ActionChains(driver)
            #             actions.move_to_element(card).perform()

            #             accedi_btn = card.find_element(By.XPATH, ".//div[@class='account-loginbutton']/button")
            #             accedi_btn.click()
            #             print("✅ Clicked 'Accedi' for selected organization.")
            #             target_found = True
            #             break
            #     except Exception as e:
            #         print(f"⚠️ Error parsing org card: {e}")
            #         continue

            # if not target_found:
            #     print(f"❌ Target organization '{TARGET_ORGANIZATION}' not found.")
            #     return

            # print("⏳ Waiting for dashboard to load...")
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
                ensure_logged_in()
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

    finally:
        driver.quit()
# scrape_customer_data_task.delay()