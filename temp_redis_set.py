import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

with open('token_haze.txt', 'r') as f:
    content = f.read()

r.set('token_haze', content)
print("Stored token_haze.txt content in Redis")