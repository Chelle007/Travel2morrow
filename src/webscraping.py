from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

def get_quote_income(policy_type, coverage_type, destination, departure_date, arriving_date, left_singapore):
    # Set up WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in background (remove if debugging)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # Open the insurance page
        driver.get("https://www.income.com.sg/buy/travel-insurance")

        # Wait for form elements to load
        wait = WebDriverWait(driver, 10)

        # Select policy type
        if (policy_type == "per-trip"):
            policy_id = "evgTripPolicy"
        elif (policy_type == "yearly"):
            policy_id = "evgYearlyPolicy"
        else:
            raise Exception("Invalid policy type: " + policy_type)
        policy_selector = wait.until(EC.element_to_be_clickable((By.ID, policy_id)))
        policy_selector.click()

        driver.execute_script(f"window.scrollBy(0, 600);")
        # TODO: yearly and per-trip has diff date option btw

        # Select coverage type
        if (coverage_type == "individual"):
            coverage_id = "Individual/Group"
        elif (coverage_type == "family"):
            coverage_id = "Family"
        else:
            raise Exception("Invalid coverage type: " + coverage_type)
        coverage_selector = wait.until(EC.element_to_be_clickable((By.XPATH, f"//li[@data-target='coverageType' and @data-value='{coverage_id}']")))
        driver.execute_script("arguments[0].click();", coverage_selector)

        driver.execute_script(f"window.scrollBy(0, 200);")

        # Select destination
        destination_selector = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Select destination(s)')]")))
        destination_selector.click()

        need_scroll = False

        if (destination == 'one-or-more'):
            region = 'One or more countries'
        elif (destination == 'asean'):
            region = 'ASEAN'
        elif (destination == 'asia'):
            region = 'Asia'
            need_scroll = True
        elif (destination == 'worldwide'):
            region = 'Worldwide'
            need_scroll = True
        else:
            raise Exception("Invalid destination: " + destination)

        region_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"label[data-value='{region}']")))
        region_input.click()

        if (destination == 'asean' or destination == 'asia' or destination == 'worldwide'):
            understand_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'I UNDERSTAND')]")))
            understand_button.click()

        # Input departure date
        departure_input = driver.find_element(By.ID, "departureDate")
        departure_input.send_keys(departure_date)

        # Input arriving date
        arriving_input = driver.find_element(By.ID, "arrivingDate")
        arriving_input.send_keys(arriving_date)

        # Select left Singapore option
        if left_singapore:
            left_sg_checkbox = driver.find_element(By.ID, "leftSingapore")
            if not left_sg_checkbox.is_selected():
                left_sg_checkbox.click()
        
        # Click consent checkbox
        consent_checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@class='checkmark']")))
        driver.execute_script("arguments[0].click();", consent_checkbox)

        # Click "Get Quote" button
        get_quote_button = driver.find_element(By.ID, "getQuote")
        get_quote_button.click()

        # Wait for results to load
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "plan-pricing")))

        # Extract prices
        plans = ["Classic", "Deluxe", "Preferred"]
        prices = {}

        for plan in plans:
            price_element = driver.find_element(By.XPATH, f"//div[contains(text(), '{plan}')]/following-sibling::div[contains(@class, 'price')]")
            prices[plan] = price_element.text

        return prices
    
    finally:
        driver.quit()

# Example usage
quote = get_quote_income("per-trip", "individual", "asean", "2025-04-01", "2025-04-10", False)
# print(quote)
