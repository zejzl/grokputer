#!/usr/bin/env python3
"""
Redis Backup Script for Grokputer
Dumps all keys and values from Redis DB 0 to a JSON file in ./vault/redis_backup.json.
Handles string values; for complex types, serializes to JSON if possible.
Run: python backup_redis.py
"""

import redis
import json
import os
import boto3
from datetime import datetime

# Config
REDIS_HOST = 'localhost'
REDIS_PORT = 6380
REDIS_DB = 0
BACKUP_FILE = './vault/redis_backup.json'

def backup_redis():
    """Backup Redis to JSON file."""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        r.ping()  # Test connection
        
        # Get all keys
        keys = r.keys('*')
        backup_data = {}
        
        for key in keys:
            try:
                value = r.get(key)
                if value is None:
                    value = r.hgetall(key) if r.type(key) == b'hash' else r.lrange(key, 0, -1) if r.type(key) == b'list' else None
                backup_data[key] = value
            except Exception as e:
                print(f"Error backing up key {key}: {e}")
                backup_data[key] = {'error': str(e)}
        
        # Ensure vault dir exists
        os.makedirs(os.path.dirname(BACKUP_FILE), exist_ok=True)
        
        # Save with metadata
        full_backup = {
            'backup_timestamp': datetime.now().isoformat(),
            'redis_host': REDIS_HOST,
            'redis_port': REDIS_PORT,
            'redis_db': REDIS_DB,
            'total_keys': len(backup_data),
            'data': backup_data
        }
        
        with open(BACKUP_FILE, 'w') as f:
            json.dump(full_backup, f, indent=2, default=str)  # default=str for non-serializable

        print(f"Redis backup complete: {len(backup_data)} keys saved to {BACKUP_FILE}")

        # Upload to S3 if configured
        s3_bucket = os.getenv('S3_BUCKET_NAME')
        if s3_bucket:
            try:
                s3_client = boto3.client('s3')
                s3_key = f"redis_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                s3_client.upload_file(BACKUP_FILE, s3_bucket, s3_key)
                print(f"Uploaded to S3: s3://{s3_bucket}/{s3_key}")
            except Exception as e:
                print(f"S3 upload failed: {e}")
        else:
            print("S3_BUCKET_NAME not set, skipping remote upload")
        
    except redis.ConnectionError:
        print("Redis connection failed. Is Redis running?")
    except Exception as e:
        print(f"Backup failed: {e}")

if __name__ == '__main__':
    backup_redis()
