from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Your Rentman credentials (replace with your actual credentials)
EMAIL = "informatica@netick.it"
PASSWORD = "Netickpass13"

# Set up Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    # Open Rentman homepage
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
        driver.get(login_url)  # Navigate to the login page
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

        # Wait for the "Accedi" button to appear and click it
        accedi_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@class='account-loginbutton']/button"))
        )
        accedi_button.click()
        print("✅ 'Accedi' button clicked! Navigating to the organization dashboard...")

        # Wait for the dashboard to load
        WebDriverWait(driver, 15).until(EC.url_contains("rentmanapp.com"))
        print("🎉 Successfully entered the organization's dashboard!")

        # Wait for the sidebar menu to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "rm-navigation__item-wrapper"))
        )
        print("✅ Sidebar menu loaded!")

        # Scroll to the "Contatti" button to ensure it's visible
        contatti_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class,'rm-navigation__item-label') and contains(text(), 'Contatti')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", contatti_button)
        print("✅ Scrolled to 'Contatti' button.")

        # Use JavaScript click to bypass hidden elements issue
        driver.execute_script("arguments[0].click();", contatti_button)
        print("✅ 'Contatti' button clicked! Navigating to contacts page...")

        # Wait for the contacts page to load
        WebDriverWait(driver, 10).until(EC.url_contains("contacts"))
        print("🎉 Successfully reached the contacts page!")

    else:
        print("❌ Login URL not found!")

except Exception as e:
    print("⚠️ Error:", e)

# Keep browser open for debugging
input("Press Enter to close the browser...")

# Close the browser
driver.quit()