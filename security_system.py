import logging
import time
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Analytics
analytics = defaultdict(int)

def log_event(event):
    logger.info(f"Event: {event}")
    analytics[event] += 1

def get_analytics():
    return dict(analytics)

# Basic security check
def check_input(user_input):
    if len(user_input) > 100:
        log_event("Suspicious long input")
        return False
    return True

if __name__ == "__main__":
    log_event("System started")
    while True:
        user_input = input("Enter command: ")
        if check_input(user_input):
            log_event(f"Processed: {user_input}")
        else:
            log_event("Input rejected")
        print("Analytics:", get_analytics())
        time.sleep(1)