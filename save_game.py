import json
import os
from datetime import datetime
from pathlib import Path

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
    
    def save_state(self, game_data, player_name="player"):
        timestamp = datetime.now().isoformat().replace(":", "-")
        save_file = self.save_dir / f"{player_name}_{timestamp}.json"
        
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
            json.dump(state, f, indent=2)
        
        print(f"Game saved to {save_file}")
        return save_file
    
    def load_state(self, save_file_path):
        if not Path(save_file_path).exists():
            raise FileNotFoundError(f"Save file not found: {save_file_path}")
        
        with open(save_file_path, 'r') as f:
            state = json.load(f)
        
        print(f"Game loaded from {save_file_path}")
        return state["game_data"]
    
    def list_saves(self, player_name=None):
        saves = list(self.save_dir.glob("*.json"))
        if player_name:
            saves = [s for s in saves if player_name in s.name]
        
        for save in sorted(saves, reverse=True):
            mod_time = datetime.fromtimestamp(save.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"{save.name} - {mod_time}")
        
        return saves

# Example usage
if __name__ == "__main__":
    saver = GameSaver()
    
    # Sample game data
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
