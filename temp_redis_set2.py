import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

with open('token_haze.py', 'r') as f:
    content = f.read()

r.set('token_haze_py', content)
print("Stored token_haze.py content in Redis")