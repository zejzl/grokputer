import time
from collections import deque
import hashlib

# Rate limiting
requests = deque()
RATE_LIMIT = 10  # requests per minute
TIME_WINDOW = 60

def is_rate_limited(ip):
    now = time.time()
    requests.append((now, ip))
    # Remove old requests
    while requests and requests[0][0] < now - TIME_WINDOW:
        requests.popleft()
    count = sum(1 for t, i in requests if i == ip)
    if count > RATE_LIMIT:
        return True
    return False

# Basic encryption (hashing for passwords)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Advanced input validation
def validate_input(user_input, allowed_chars='a-zA-Z0-9 '):
    if any(char not in allowed_chars for char in user_input):
        return False
    return True