import redis
import time
import json

# Connect to Redis (exposed port from Docker)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

channel = 'grokputer_broadcast'

def publish_ping():
    message = {
        'type': 'ping',
        'from': 'local_runner',
        'timestamp': time.time(),
        'payload': 'Hello from local host!'
    }
    r.publish(channel, json.dumps(message))
    print(f"Published ping to {channel}: {message}")

def listen_for_responses(duration=10):
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    print(f"Listening on {channel} for {duration}s...")
    start = time.time()
    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            print(f"Received: {data}")
        if time.time() - start > duration:
            break
    pubsub.unsubscribe()

if __name__ == '__main__':
    publish_ping()
    listen_for_responses()
