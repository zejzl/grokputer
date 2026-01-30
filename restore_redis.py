#!/usr/bin/env python3
"""
Redis Restore Script for Grokputer
Restores keys and values from ./vault/redis_backup.json to Redis DB 0.
Handles strings, hashes, lists; skips errors for complex types.
Run: python restore_redis.py
Warning: Overwrites existing keys—backup first!
"""

import redis
import json
import os
from datetime import datetime

# Config
REDIS_HOST = 'localhost'
REDIS_PORT = 6380
REDIS_DB = 0
BACKUP_FILE = './vault/redis_backup.json'

def restore_redis():
    """Restore Redis from JSON backup file."""
    if not os.path.exists(BACKUP_FILE):
        print(f"Backup file not found: {BACKUP_FILE}")
        return
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        r.ping()  # Test connection
        
        with open(BACKUP_FILE, 'r') as f:
            full_backup = json.load(f)
        
        data = full_backup.get('data', {})
        restored_count = 0
        errors = []
        
        for key, value in data.items():
            try:
                if isinstance(value, dict) and 'error' not in value:
                    # Assume hash
                    r.hset(key, mapping=value)
                elif isinstance(value, list):
                    # Assume list
                    r.rpush(key, *value)
                elif value is not None:
                    # String
                    r.set(key, value)
                else:
                    errors.append(f"Skipped {key}: Unknown type")
                    continue
                
                restored_count += 1
                print(f"Restored {key}")
                
            except Exception as e:
                errors.append(f"Error restoring {key}: {e}")
        
        print(f"Redis restore complete: {restored_count} keys restored from {full_backup.get('total_keys', 0)} total.")
        if errors:
            print("Errors:", errors)
        else:
            print("No errors.")
            
    except redis.ConnectionError:
        print("Redis connection failed. Is Redis running?")
    except json.JSONDecodeError as e:
        print(f"Invalid backup JSON: {e}")
    except Exception as e:
        print(f"Restore failed: {e}")

if __name__ == '__main__':
    print("WARNING: This will overwrite existing Redis keys. Ensure backup is recent.")
    confirm = input("Type 'YES' to proceed: ")
    if confirm == 'YES':
        restore_redis()
    else:
        print("Restore aborted.")
