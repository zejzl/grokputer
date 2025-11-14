import json
import os
import redis
from datetime import datetime
from pathlib import Path
from toon_format import encode, decode

"""
GameSaver Module
================

A simple utility for saving and loading game states in JSON format.
Designed for text-based or simple Python games, with potential integration
into larger systems like Grokputer for state persistence in ORAM loops.

Features:
- Timestamped saves in a dedicated directory.
- Player-specific filtering.
- Basic error handling for file operations.
- Example usage included.

Integration Ideas:
- Hook into Grokputer's Memory Manager for hierarchical persistence.
- Use with Pantheon agents: e.g., Analyzer saves metrics, Learner loads patterns.

Requirements: Python 3.7+ (uses pathlib).

Example Usage:
    saver = GameSaver('my_saves')
    data = {'level': 5, 'score': 1000}
    save_path = saver.save_state(data, 'player1')
    loaded = saver.load_state(save_path)
    saver.list_saves('player1')

For Grokputer: Call save_state in Improver for post-task snapshots.
Add to README.md: "Use GameSaver for persistent memory in autonomous loops."
"""

class GameSaver:
    """
    Main class for handling game state saves and loads.
    
    Args:
        save_dir (str): Directory to store save files. Defaults to "saves".
    """
    def __init__(self, save_dir="saves"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    def save_state(self, game_data, player_name="player"):
        timestamp = datetime.now().isoformat().replace(":", "-")
        save_file = self.save_dir / f"{player_name}_{timestamp}.toon"

        state = {
            "timestamp": timestamp,
            "player": player_name,
            "game_data": game_data,
            "metadata": {
                "version": "1.0",
                "location": str(save_file)
            }
        }

        with open(save_file, 'w') as f:
            f.write(encode(state))
        
        print(f"Game saved to {save_file}")
        return save_file

    def save_to_redis(self, game_data, player_name="player", key_prefix="game"):
        try:
            key = f"{key_prefix}:{player_name}"
            self.redis_client.set(key, json.dumps(game_data))
            print(f"Game saved to Redis: {key}")
        except redis.ConnectionError:
            print("Redis connection failed. Skipping Redis save.")
        except Exception as e:
            print(f"Redis save failed: {e}")

    def load_from_redis(self, player_name="player", key_prefix="game"):
        try:
            key = f"{key_prefix}:{player_name}"
            data = self.redis_client.get(key)
            if data:
                loaded = json.loads(data)
                print(f"Game loaded from Redis: {key}")
                return loaded
            else:
                raise ValueError(f"No data found for {key}")
        except redis.ConnectionError:
            print("Redis connection failed.")
            raise
        except Exception as e:
            print(f"Redis load failed: {e}")
            raise
    
    def load_state(self, save_file_path):
        if not Path(save_file_path).exists():
            raise FileNotFoundError(f"Save file not found: {save_file_path}")

        with open(save_file_path, 'r') as f:
            data = f.read()
            state = decode(data)

        print(f"Game loaded from {save_file_path}")
        return state["game_data"]
    
    def list_saves(self, player_name=None):
        saves = list(self.save_dir.glob("*.toon"))
        if player_name:
            saves = [s for s in saves if player_name in s.name]
        
        for save in sorted(saves, reverse=True):
            mod_time = datetime.fromtimestamp(save.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"{save.name} - {mod_time}")
        
        return saves

# Example usage
def main():
    import argparse
    import time
    import threading

    parser = argparse.ArgumentParser(description="Grokputer Game Saver")
    parser.add_argument("--auto", action="store_true", help="Auto-save with default data")
    parser.add_argument("--interval", type=int, help="Auto-save interval in minutes (runs as daemon)")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon with default 15min interval")

    args = parser.parse_args()

    saver = GameSaver()

    if args.daemon or args.interval:
        interval_minutes = args.interval or 15
        interval_seconds = interval_minutes * 60

        def backup_daemon():
            while True:
                try:
                    # Sample game data (in real usage, this would collect actual state)
                    sample_data = {
                        "level": 5,
                        "score": 1500,
                        "inventory": ["sword", "potion"],
                        "position": {"x": 10, "y": 20},
                        "timestamp": time.time(),
                        "auto_backup": True
                    }

                    save_path = saver.save_state(sample_data, "auto_backup")
                    saver.save_to_redis(sample_data, "auto_backup")
                    print(f"[AUTO-BACKUP] Saved at {time.strftime('%Y-%m-%d %H:%M:%S')}: {save_path}")

                except Exception as e:
                    print(f"[AUTO-BACKUP] Error: {e}")

                time.sleep(interval_seconds)

        print(f"[AUTO-BACKUP] Starting daemon with {interval_minutes}min intervals...")
        daemon_thread = threading.Thread(target=backup_daemon, daemon=True)
        daemon_thread.start()

        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[AUTO-BACKUP] Stopped by user")

    else:
        # Manual save mode
        sample_data = {
            "level": 5,
            "score": 1500,
            "inventory": ["sword", "potion"],
            "position": {"x": 10, "y": 20}
        }

        # Save
        save_path = saver.save_state(sample_data, "hero")

        # List saves
        saver.list_saves("hero")

        # Load (example)
        # loaded_data = saver.load_state(save_path)
        # print("Loaded:", loaded_data)

if __name__ == "__main__":
    main()
