import redis
import time
import json

# Connect to Redis
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

channel = "grokputer_broadcast"


def throughput_test(num_messages=10000):
    start_time = time.time()
    messages_sent = 0

    for i in range(num_messages):
        message = {"type": "test", "id": i, "timestamp": time.time()}
        r.publish(channel, json.dumps(message))
        messages_sent += 1

        if i % 1000 == 0:
            print(f"Sent {i} messages...")

    end_time = time.time()
    duration = end_time - start_time
    rate = num_messages / duration if duration > 0 else 0

    print(f"\nThroughput test completed:")
    print(f"Messages sent: {num_messages}")
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Messages per second: {rate:.2f}")


if __name__ == "__main__":
    throughput_test(10000)
