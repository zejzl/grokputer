import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from toon_format import encode, decode

# Optional Redis import
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

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
        if REDIS_AVAILABLE:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        else:
            self.redis_client = None

        # SQLite setup
        self.db_path = self.save_dir / "saves.db"
        self.db_conn = sqlite3.connect(str(self.db_path))
        self._create_table()

    def _create_table(self):
        """Create the saves table if it doesn't exist."""
        cursor = self.db_conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                game_data TEXT NOT NULL,
                file_path TEXT
            )
        ''')
        self.db_conn.commit()
    
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

        # Also save to SQLite for backup
        self.save_to_sqlite(game_data, player_name, save_file)

        print(f"Game saved to {save_file}")
        return save_file

    def save_to_sqlite(self, game_data, player_name="player", file_path=None):
        """Save game data to SQLite database."""
        try:
            timestamp = datetime.now().isoformat()
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO saves (player_name, timestamp, game_data, file_path)
                VALUES (?, ?, ?, ?)
            ''', (player_name, timestamp, json.dumps(game_data), str(file_path) if file_path else None))
            self.db_conn.commit()
            print(f"Game saved to SQLite: {player_name} at {timestamp}")
        except Exception as e:
            print(f"SQLite save failed: {e}")

    def save_to_redis(self, game_data, player_name="player", key_prefix="game"):
        if not REDIS_AVAILABLE or self.redis_client is None:
            print("Redis not available. Skipping Redis save.")
            return
        try:
            key = f"{key_prefix}:{player_name}"
            self.redis_client.set(key, json.dumps(game_data))
            print(f"Game saved to Redis: {key}")
        except redis.ConnectionError:
            print("Redis connection failed. Skipping Redis save.")
        except Exception as e:
            print(f"Redis save failed: {e}")

    def load_from_sqlite(self, player_name="player", limit=1):
        """Load latest game data from SQLite database."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                SELECT game_data, timestamp FROM saves
                WHERE player_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (player_name, limit))
            rows = cursor.fetchall()
            if rows:
                game_data = json.loads(rows[0][0])
                timestamp = rows[0][1]
                print(f"Game loaded from SQLite: {player_name} at {timestamp}")
                return game_data
            else:
                raise ValueError(f"No data found for {player_name}")
        except Exception as e:
            print(f"SQLite load failed: {e}")
            raise

    def load_from_redis(self, player_name="player", key_prefix="game"):
        if not REDIS_AVAILABLE or self.redis_client is None:
            print("Redis not available.")
            raise RuntimeError("Redis not available")
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
                    # SQLite save is already done in save_state
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
