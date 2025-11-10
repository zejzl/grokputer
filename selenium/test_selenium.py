import time
import logging
import json
import redis
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from PIL import Image
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/selenium.log'),
        logging.StreamHandler()  # For docker-compose output
    ]
)
logger = logging.getLogger(__name__)

# Connect to Redis for message bus
r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
channel = 'grokputer_broadcast'

def publish_message(msg_type, payload):
    message = {
        'type': msg_type,
        'from': 'selenium_agent',
        'timestamp': time.time(),
        'payload': payload
    }
    r.publish(channel, json.dumps(message))
    logger.info(f"Published {msg_type} message to {channel}")

def take_screenshot_and_log(driver, test_name):
    try:
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(screenshot))
        size = len(screenshot)
        logger.info(f"{test_name} - Screenshot captured, size: {size} bytes")
        return size
    except Exception as e:
        logger.error(f"{test_name} - Screenshot failed: {e}")
        return 0

start_time = time.time()

# Publish ready message
publish_message('browser_ready', {'status': 'initialized', 'capabilities': 'headless firefox'})

options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)

tests_passed = 0
total_tests = 4
test_results = []

try:
    # Test 1: Basic navigation to Google and title check
    test_start = time.time()
    load_start = time.time()
    driver.get("https://www.google.com/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "title")))
    load_time = time.time() - load_start
    title = driver.title
    screenshot_size1 = take_screenshot_and_log(driver, "Test 1")
    test_time = time.time() - test_start
    if "Google" in title:
        logger.info("Test 1 PASSED: Google loaded, title contains 'Google'")
        tests_passed += 1
        result = {'passed': True, 'load_time': load_time, 'screenshot_size': screenshot_size1}
    else:
        logger.error("Test 1 FAILED: Unexpected title")
        result = {'passed': False, 'load_time': load_time, 'screenshot_size': 0}
    test_results.append(result)
    logger.info(f"Test 1 total time: {test_time:.2f} seconds")

    # Test 2: Perform a search on Google and verify results
    test_start = time.time()
    load_start = time.time()
    search_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q")))
    search_box.send_keys("Selenium test")
    search_box.submit()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "search")))
    load_time = time.time() - load_start
    title = driver.title
    screenshot_size2 = take_screenshot_and_log(driver, "Test 2")
    test_time = time.time() - test_start
    if "Selenium test" in title:
        logger.info("Test 2 PASSED: Search performed, title contains query")
        tests_passed += 1
        result = {'passed': True, 'load_time': load_time, 'screenshot_size': screenshot_size2}
    else:
        logger.error("Test 2 FAILED: Search results not loaded")
        result = {'passed': False, 'load_time': load_time, 'screenshot_size': 0}
    test_results.append(result)
    logger.info(f"Test 2 total time: {test_time:.2f} seconds")

    # Test 3: Navigate to example.com
    test_start = time.time()
    load_start = time.time()
    driver.get("https://example.com")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    load_time = time.time() - load_start
    h1_text = driver.find_element(By.TAG_NAME, "h1").text
    screenshot_size3 = take_screenshot_and_log(driver, "Test 3")
    test_time = time.time() - test_start
    if h1_text == "Example Domain":
        logger.info("Test 3 PASSED: example.com loaded, H1 is 'Example Domain'")
        tests_passed += 1
        result = {'passed': True, 'load_time': load_time, 'screenshot_size': screenshot_size3}
    else:
        logger.error("Test 3 FAILED: Unexpected H1 text")
        result = {'passed': False, 'load_time': load_time, 'screenshot_size': 0}
    test_results.append(result)
    logger.info(f"Test 3 total time: {test_time:.2f} seconds")

    # Test 4: Simple interaction - Click a link on example.com (more link)
    test_start = time.time()
    load_start = time.time()
    more_link = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "More information")))
    more_link.click()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "p")))
    load_time = time.time() - load_start
    p_text = driver.find_element(By.TAG_NAME, "p").text
    screenshot_size4 = take_screenshot_and_log(driver, "Test 4")
    test_time = time.time() - test_start
    if "IANA" in p_text:
        logger.info("Test 4 PASSED: Link clicked, IANA paragraph visible")
        tests_passed += 1
        result = {'passed': True, 'load_time': load_time, 'screenshot_size': screenshot_size4}
    else:
        logger.error("Test 4 FAILED: Link click or paragraph not as expected")
        result = {'passed': False, 'load_time': load_time, 'screenshot_size': 0}
    test_results.append(result)
    logger.info(f"Test 4 total time: {test_time:.2f} seconds")

except TimeoutException as e:
    logger.error(f"Timeout in test: {e}")
    test_results.append({'passed': False, 'error': str(e)})
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    test_results.append({'passed': False, 'error': str(e)})

driver.quit()

total_time = time.time() - start_time
summary = {
    'tests_passed': tests_passed,
    'total_tests': total_tests,
    'test_results': test_results,
    'total_time': total_time,
    'status': 'success' if tests_passed == total_tests else 'partial'
}
publish_message('selenium_tests_completed', summary)

logger.info(f"Overall: {tests_passed}/{total_tests} tests passed in {total_time:.2f} seconds")
logger.info("All tests completed.")