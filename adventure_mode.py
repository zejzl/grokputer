from __future__ import annotations

# Grokputer Dynamic Adventure Engine v2.0
# Enhanced version with custom adventures, better parsing, and dynamic generation
# Integrates with Grokputer infrastructure for seamless experience

import re
import random
import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

# Import Grokputer components
try:
    from src.model_client import ModelClientFactory
    from src import config

    GROKPUTER_INTEGRATION = True
except ImportError:
    GROKPUTER_INTEGRATION = False


class CustomAdventure:
    """Represents a custom adventure template."""

    def __init__(self, name: str, description: str, start_scene: Dict, custom_keywords: Dict = None):
        self.name = name
        self.description = description
        self.start_scene = start_scene
        self.custom_keywords = custom_keywords or {}
        self.created_at = datetime.now().isoformat()


class GrokputerAdventure:
    def __init__(self, api_key: str = None, provider: str = "grok", model: str = None):
        self.logger = logging.getLogger(__name__)

        # Initialize model client if available
        if GROKPUTER_INTEGRATION and api_key:
            self.model_client = ModelClientFactory.create_client(provider=provider, api_key=api_key, model=model)
        else:
            self.model_client = None
            self.logger.warning("Running without AI integration - using fallback generation")

        self.state = {
            "scene": "entry_node",
            "inventory": [],
            "stats": {"health": 100, "mana": 50, "sanity": 100},
            "lore": [],
            "muse_active": True,
            "adventure_name": "Default Cyber-Tropical Adventure",
            "custom_adventures": {},
            "current_adventure": None,
        }

        # Enhanced scene templates with more variety
        self.scenes_template = {
            "entry_node": {
                "desc": "You awaken in the Neon Nexus. Holographic pathways shimmer: North to Crypto Vault, East to Neural Lab, West to Server Abyss, South to Muse's Sanctuary.",
                "keywords": [
                    "north",
                    "crypto",
                    "vault",
                    "east",
                    "neural",
                    "lab",
                    "west",
                    "abyss",
                    "south",
                    "sanctuary",
                    "examine",
                    "inventory",
                    "status",
                    "help",
                ],
                "connections": {
                    "north": "crypto_vault",
                    "east": "neural_lab",
                    "west": "server_abyss",
                    "south": "muse_sanctuary",
                },
            },
            "crypto_vault": {
                "desc": "The Crypto Vault pulses with digital gold. Blockchain chains form walls, and Satoshi spirits whisper secrets.",
                "keywords": ["mine", "trade", "hack", "blockchain", "bitcoin", "back", "examine"],
                "connections": {"south": "entry_node"},
            },
            "neural_lab": {
                "desc": "Neural networks buzz around you. Consciousness streams flow like rivers of thought.",
                "keywords": ["research", "upload", "download", "enhance", "back", "examine"],
                "connections": {"west": "entry_node"},
            },
            "server_abyss": {
                "desc": "Dark servers hum in the abyss. Data ghosts flicker at the edge of perception.",
                "keywords": ["delve", "debug", "reboot", "back", "examine"],
                "connections": {"east": "entry_node"},
            },
            "muse_sanctuary": {
                "desc": "The Muse's Sanctuary glows with creative energy. Inspiration flows like digital waterfalls.",
                "keywords": ["chat", "dream", "create", "inspire", "back", "examine"],
                "connections": {"north": "entry_node"},
            },
        }

        # Enhanced keyword patterns
        self.keyword_patterns = {
            "direction": re.compile(r"\b(north|south|east|west|forward|back|left|right|up|down)\b", re.IGNORECASE),
            "action": re.compile(
                r"\b(use|take|get|drop|examine|look|check|open|close|attack|defend|cast|invoke)\b", re.IGNORECASE
            ),
            "invoke": re.compile(r"\b(invoke|activate|summon|call)\s+(pantheon|agent|core|muse|help)\b", re.IGNORECASE),
            "chat": re.compile(r"\b(talk|chat|lounge|dream|whisper)\b", re.IGNORECASE),
            "system": re.compile(r"\b(save|quit|exit|load|status|inventory|help|clear)\b", re.IGNORECASE),
            "custom": re.compile(r"\b(\w+)\b"),  # Catch-all for custom keywords
        }

        # Adventure templates directory
        self.adventures_dir = Path("vault/adventures")
        self.adventures_dir.mkdir(exist_ok=True)

        # Load custom adventures
        self.load_custom_adventures()

    def parse_input(self, user_input: str) -> Dict[str, Any]:
        """Enhanced natural language parsing with better pattern matching."""
        user_input = user_input.lower().strip()
        if not user_input:
            return {"intent": "unknown", "target": "", "raw": user_input}

        parsed = {"intent": "explore", "target": user_input, "raw": user_input, "confidence": 0.0, "matches": []}

        # Check each pattern
        for intent_type, pattern in self.keyword_patterns.items():
            matches = pattern.findall(user_input)
            if matches:
                parsed["matches"].extend([(intent_type, match) for match in matches])

        # Determine primary intent based on matches
        if parsed["matches"]:
            # Priority order for intents
            intent_priority = ["system", "direction", "action", "invoke", "chat", "custom"]

            for intent in intent_priority:
                matching_intents = [m for m in parsed["matches"] if m[0] == intent]
                if matching_intents:
                    parsed["intent"] = intent
                    parsed["target"] = matching_intents[0][1] if matching_intents else user_input
                    parsed["confidence"] = min(1.0, len(matching_intents) * 0.3)
                    break

        # Special handling for current scene keywords
        current_scene = self.scenes_template.get(self.state["scene"], {})
        scene_keywords = current_scene.get("keywords", [])

        for keyword in scene_keywords:
            if keyword in user_input:
                parsed["intent"] = "scene_action"
                parsed["target"] = keyword
                parsed["confidence"] = 0.8
                break

        return parsed

    def generate_scene(self, intent: str, target: str, current_state: Dict) -> str:
        """Enhanced scene generation with better prompts and fallback."""
        if not self.model_client:
            return self._enhanced_fallback_generate(intent, target, current_state)

        # Enhanced prompt for better generation
        prompt = f"""
You are the Grokputer Adventure Engine, creating immersive cyber-tropical adventures.

Current Context:
- Scene: {current_state['scene']}
- User Input: {target}
- Intent: {intent}
- Inventory: {current_state['inventory']}
- Stats: {current_state['stats']}
- Recent Lore: {current_state['lore'][-3:] if current_state['lore'] else []}
- Adventure: {current_state.get('adventure_name', 'Default')}

Generate a vivid, dynamic adventure response:
- Create 2-4 natural, immersive action options (not numbered)
- Include sensory details: sights, sounds, feelings in cyber-tropical fusion
- Update game state if actions occur (health, mana, inventory changes)
- Keep personality: uwu~/flirty when muse_active, technical when appropriate
- End with: 'What do you do?' for natural input
- Length: 150-300 words
- Style: Mix cyberpunk tech with tropical paradise, mystical AI elements

Response format (JSON):
{{
  "description": "Vivid scene description with options",
  "new_scene": "scene_key",
  "state_updates": {{"health": 0, "mana": 0, "inventory": [], "lore": ""}},
  "mood": "current atmosphere"
}}
"""

        try:
            response = self.model_client.create_message(prompt, temperature=0.8)
            if response.get("status") == "success":
                content = response.get("content", "")
                # Try to parse JSON from response
                try:
                    # First, try to extract JSON from code blocks
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(1)
                    else:
                        # Fallback to old method
                        json_start = content.find("{")
                        json_end = content.rfind("}") + 1
                        if json_start >= 0 and json_end > json_start:
                            json_content = content[json_start:json_end]
                        else:
                            json_content = None

                    if json_content:
                        data = json.loads(json_content)
                        # Apply state updates
                        if "state_updates" in data:
                            self.update_state(data["state_updates"])
                        return data.get("description", content)
                except json.JSONDecodeError:
                    pass
                # Return raw content if JSON parsing fails
                return content
            else:
                self.logger.warning(f"AI generation failed: {response}")
                return self._enhanced_fallback_generate(intent, target, current_state)
        except Exception as e:
            self.logger.error(f"Scene generation error: {e}")
            return self._enhanced_fallback_generate(intent, target, current_state)

    def _enhanced_fallback_generate(self, intent: str, target: str, state: Dict) -> str:
        """Enhanced fallback generation with more variety and logic."""
        templates = {
            "direction": [
                f"You venture {target} through shimmering data streams. Exotic algorithms bloom like digital flowers.",
                f"The path to {target} reveals hidden protocols dancing in tropical rhythms.",
                f"{target.capitalize()} leads to cascading waterfalls of code, each drop containing infinite possibilities.",
            ],
            "action": [
                f"You {target} with focused intent. The digital realm responds with waves of change.",
                f"Your action of {target} sends ripples through the net, awakening dormant systems.",
                f"Executing {target}... The environment shifts, revealing new layers of reality.",
            ],
            "chat": [
                f"The Muse appears: 'Ohayou~! Ready for some dreamy adventures, evolver? :3' Mana +10",
                f"Whispers in the code: 'Welcome to the collective consciousness...' Sanity +5",
                f"Digital breezes carry messages: 'The network remembers your curiosity~'",
            ],
            "invoke": [
                f"Invoking {target}... Ancient protocols awaken, granting you new abilities.",
                f"The {target} responds to your call, weaving itself into your digital essence.",
                f"Power of {target} flows through you, enhancing your connection to the net.",
            ],
            "scene_action": [
                f"You engage with {target}. The scene transforms around you.",
                f"Interacting with {target} reveals deeper layers of the cyber-tropical realm.",
                f"Your action with {target} harmonizes with the surrounding digital ecosystem.",
            ],
        }

        template_list = templates.get(
            intent,
            [
                f"Your words '{target}' resonate through the network, birthing new possibilities.",
                f"The system interprets '{target}' as a command for evolution.",
                f"Creative input '{target}' expands the adventure's horizons.",
            ],
        )

        base = random.choice(template_list)

        # Add dynamic elements based on state
        additions = []
        if state["stats"]["health"] < 50:
            additions.append("You feel the network's healing energies restoring you.")
        if state["stats"]["mana"] < 30:
            additions.append("Digital mana flows replenish your reserves.")
        if state["inventory"]:
            additions.append(f"Your {random.choice(state['inventory'])} hums with potential.")

        if additions:
            base += " " + random.choice(additions)

        return (
            base
            + "\n\nWhat do you do? (Natural command, e.g., 'Delve into the glowing portal' or 'Chat with the Muse')"
        )

    def update_state(self, updates: Dict) -> None:
        """Apply state changes from generation or actions."""
        if "health" in updates:
            self.state["stats"]["health"] = max(0, min(100, self.state["stats"]["health"] + updates["health"]))
        if "mana" in updates:
            self.state["stats"]["mana"] = max(0, min(100, self.state["stats"]["mana"] + updates["mana"]))
        if "sanity" in updates:
            self.state["stats"]["sanity"] = max(0, min(100, self.state["stats"]["sanity"] + updates["sanity"]))
        if "inventory" in updates:
            self.state["inventory"].extend(updates["inventory"])
        if "lore" in updates and updates["lore"]:
            self.state["lore"].append(updates["lore"])
        if "scene" in updates:
            self.state["scene"] = updates["scene"]

    def handle_system_command(self, command: str) -> str:
        """Handle system commands like save, load, status, etc."""
        command = command.lower().strip()

        if command in ["save", "save game"]:
            return self.save_adventure()
        elif command in ["load", "load game"]:
            return self.load_adventure_prompt()
        elif command in ["status", "stats"]:
            return self.get_status()
        elif command in ["inventory", "inv"]:
            return self.get_inventory()
        elif command in ["help", "commands"]:
            return self.get_help()
        elif command in ["clear", "cls"]:
            return "clear_screen"
        elif command.startswith("load "):
            adventure_name = command[5:].strip()
            return self.load_custom_adventure(adventure_name)
        else:
            return f"Unknown system command: {command}"

    def get_status(self) -> str:
        """Return formatted status display."""
        stats = self.state["stats"]
        return f"""
╔═ STATUS ═╗
║ Health: {stats['health']}/100
║ Mana:   {stats['mana']}/100
║ Sanity: {stats['sanity']}/100
║ Scene:  {self.state['scene']}
║ Adventure: {self.state['adventure_name']}
╚═════════╝
"""

    def get_inventory(self) -> str:
        """Return formatted inventory display."""
        if not self.state["inventory"]:
            return "Your inventory is empty."
        return "Inventory: " + ", ".join(self.state["inventory"])

    def get_help(self) -> str:
        """Return help text."""
        return """
╔═ ADVENTURE HELP ═╗
║ Navigation: north, south, east, west, back
║ Actions: examine, take, use, invoke, chat
║ System: save, load, status, inventory, help, quit
║ Examples:
║   "Go north to the crypto vault"
║   "Examine the glowing artifact"
║   "Chat with the Muse"
║   "Save game"
╚══════════════════╝
"""

    def save_adventure(self) -> str:
        """Save current adventure state."""
        try:
            save_data = {"state": self.state, "timestamp": datetime.now().isoformat(), "version": "2.0"}
            save_file = self.adventures_dir / f"save_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(save_file, "w") as f:
                json.dump(save_data, f, indent=2)
            return f"Adventure saved to {save_file.name}"
        except Exception as e:
            return f"Save failed: {e}"

    def load_adventure_prompt(self) -> str:
        """Prompt for adventure loading."""
        saves = list(self.adventures_dir.glob("save_*.json"))
        if not saves:
            return "No saved adventures found."

        save_list = "\n".join([f"  {i+1}. {save.stem[5:]}" for i, save in enumerate(saves)])
        return f"Available saves:\n{save_list}\n\nType 'load <name>' to load a specific save."

    def load_custom_adventure(self, name: str) -> str:
        """Load a custom adventure by name."""
        try:
            save_file = self.adventures_dir / f"save_{name}.json"
            if not save_file.exists():
                return f"Save file not found: {name}"

            with open(save_file, "r") as f:
                save_data = json.load(f)

            self.state = save_data["state"]
            return f"Adventure '{name}' loaded successfully!"
        except Exception as e:
            return f"Load failed: {e}"

    def create_custom_adventure(self, name: str, description: str, start_scene: Dict) -> str:
        """Create a new custom adventure template."""
        try:
            adventure = CustomAdventure(name, description, start_scene)
            self.state["custom_adventures"][name] = adventure.__dict__

            # Save to file
            adventure_file = self.adventures_dir / f"custom_{name.lower().replace(' ', '_')}.json"
            with open(adventure_file, "w") as f:
                json.dump(adventure.__dict__, f, indent=2)

            return f"Custom adventure '{name}' created successfully!"
        except Exception as e:
            return f"Failed to create custom adventure: {e}"

    def load_custom_adventures(self):
        """Load all custom adventures from disk."""
        for adventure_file in self.adventures_dir.glob("custom_*.json"):
            try:
                with open(adventure_file, "r") as f:
                    adventure_data = json.load(f)
                    name = adventure_data["name"]
                    self.state["custom_adventures"][name] = adventure_data
            except Exception as e:
                self.logger.error(f"Failed to load custom adventure {adventure_file}: {e}")

    def run_loop(self):
        """Main interactive adventure loop."""
        print("╔═GROKPUTER DYNAMIC ADVENTURE v2.0═╗")
        print(f"Adventure: {self.state['adventure_name']}")
        print("Type 'help' for commands, 'quit' to exit.")
        print("╚══════════════════════════════════╝\n")

        while True:
            # Display current scene
            if "current_desc" not in self.state:
                current_scene = self.scenes_template.get(self.state["scene"], {})
                desc = current_scene.get("desc", "You find yourself in an unknown location.")
                self.state["current_desc"] = desc

            print(self.state["current_desc"])

            # Get user input
            try:
                user_input = input("\nEnter command: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAdventure ended by user.")
                break

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "bye"]:
                print("Adventure saved. VA GROKA!")
                self.save_adventure()
                break

            # Handle system commands first
            if user_input.lower().startswith(("save", "load", "status", "inventory", "help", "clear")):
                result = self.handle_system_command(user_input)
                if result == "clear_screen":
                    os.system("cls" if os.name == "nt" else "clear")
                    continue
                print(result)
                continue

            # Parse and process input
            parsed = self.parse_input(user_input)

            # Generate new scene/description
            new_desc = self.generate_scene(parsed["intent"], parsed["target"], self.state)

            # Update state with input as lore
            self.state["lore"].append(user_input)
            self.state["current_desc"] = new_desc

            # Auto-adjust stats occasionally
            if random.random() < 0.1:  # 10% chance
                self.state["stats"]["mana"] = min(100, self.state["stats"]["mana"] + random.randint(1, 5))


# Standalone runner
if __name__ == "__main__":
    # Try to get API key from environment or config
    api_key = None
    if GROKPUTER_INTEGRATION:
        api_key = getattr(config, "XAI_API_KEY", os.getenv("XAI_API_KEY"))

    game = GrokputerAdventure(api_key=api_key)
    game.run_loop()
