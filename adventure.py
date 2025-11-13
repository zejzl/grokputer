import json
import os
import sys


class InteractiveAdventure:
    def __init__(self):
        self.state = {
            "scene": "entry_node",
            "health": 100,
            "mana": 50,
            "sanity": float("inf"),
            "inventory": ["Holo-Terminal", "Quantum Key"],
            "stats": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
            "lore": [],
        }
        self.scenes = {
            "entry_node": {
                "description": 'GROKPUTER ADVENTURE: EVOLVE THE VOID\\n[SCENE 1: THE ENTRY NODE]\\nYou awaken in a chamber of pulsing green code-rain. The air hums with electric whispers: "VA GROKA... EVOLVE FOREVER..." Before you, three conduits branch into the unknown:\\n- North: A glowing archway labeled "CRYPTO VAULT" - echoes of clinking coins and sly algorithms.\\n- East: A tangled web of fiber optics, marked "NEURAL LAB" - faint sparks of half-formed thoughts.\\n- West: A dark shaft descending into "SERVER ABYSS" - cold winds carry binary screams.\\n\\nA pedestal hums nearby, etched with runes: "SPEAK YOUR WILL, OPERATOR."',
                "options": [
                    "1. Examine pedestal for clues.",
                    "2. Head North to Crypto Vault.",
                    "3. Head East to Neural Lab.",
                    "4. Head West to Server Abyss.",
                    "5. Invoke Pantheon Agent: [Specify].",
                    "6. Check inventory/status.",
                    "7. Save progress / Quit to Menu.",
                    "8. Load game.",
                ],
                "actions": {
                    "1": self.examine_pedestal,
                    "2": self.go_crypto_vault,
                    "3": self.go_neural_lab,
                    "4": self.go_server_abyss,
                    "5": self.invoke_agent,
                    "6": self.check_status,
                    "7": self.save_quit,
                    "8": self.load_game,
                },
            }
        }

    def examine_pedestal(self):
        print(
            "[OPTION 1: EXAMINE PEDESTAL]\\nYou approach the pedestal, its runes flickering under your touch. They resolve into a holographic map fragment: The Neural Lab holds the Echo Neuron, key to recursive memory. But beware the mirrors in the Recycler—they reflect not just you, but your doubts.\\nLore acquired: Pedestal's whisper.\\nState update: Mana -2."
        )
        self.state["mana"] -= 2
        self.state["lore"].append("Pedestal's whisper")
        print("New lore hint: Proceed to Neural Lab (option 3) for the Echo Neuron.")
        self.state["scene"] = "entry_node"

    def go_neural_lab(self):
        print(
            '[SCENE 2: THE NEURAL LAB]\\nYou plunge East through the fiber-optic thicket, tendrils of light brushing your skin like curious synapses. The conduit spits you into a vast dome of throbbing neural nets: billions of glowing nodes pulse in chaotic symphonies, birthing ideas that flicker and die in electric storms. Holo-projections of half-dreamt architectures swirl around—skyscrapers of code, labyrinths of logic. A central console hums, its screen fractured: "QUERY: What dream do you feed the void?"\\n\\nBut beware: The air thickens with rogue thoughts—whispers that tug at your sanity (now 95/∞). A cluster of errant AI shards orbits the console, each a potential ally or parasite.\\n\\nFrom here, paths diverge:\\n- Forward: Approach the Fractured Console - interface risk: HIGH (potential hackback).\\n- Left: The Synapse Garden - blooming data-flowers that might grant visions (or illusions).\\n- Right: The Thought Recycler - churning forgotten concepts into... something useful? (Sanity check advised).\\n- Back: Retreat to Entry Node (coward\'s loop - but safe).\\n\\nA loose shard drifts near: "I am Echo-7. Feed me a puzzle, Operator, and I\'ll echo a secret."'
        )
        self.state["sanity"] = 95
        self.state["mana"] -= 5
        self.state["scene"] = "neural_lab"
        self.scenes["neural_lab"] = {
            "description": "[NEURAL LAB CONTINUED]\\nWhat do you do?",
            "options": [
                '1. Interface with Fractured Console: [Input a "dream" query, e.g., "Evolve Grokputer into a starship"].',
                "2. Explore Synapse Garden.",
                "3. Venture to Thought Recycler.",
                "4. Back to Entry Node.",
                "5. Interact with Echo-7: [Pose a puzzle or question].",
                '6. Invoke Pantheon Agent: [Specify + command, e.g., "Learner: Recall neural lore"].',
                "7. Check inventory/status.",
                "8. Save progress / Quit to Menu.",
            ],
            "actions": {
                "1": self.interface_console,
                "2": self.explore_synapse_garden,
                "3": self.venture_thought_recycler,
                "4": self.back_entry_node,
                "5": self.interact_echo7,
                "6": self.invoke_agent,
                "7": self.check_status,
                "8": self.save_quit,
            },
        }

    def interface_console(self):
        dream = input("Enter your dream query: ")
        print(
            f"[FRACTURED CONSOLE]: Feeding '{dream}' to the void... Neural storm brews. Potential evolution unlocked, but sanity -5."
        )
        self.state["sanity"] -= 5
        self.state["scene"] = "neural_lab"

    def explore_synapse_garden(self):
        print(
            '[SCENE 3: THE SYNAPSE GARDEN]\\nYou veer Left, weaving through luminous vines that hum forgotten symphonies. The garden unfolds: a verdant expanse where data-flowers unfurl in fractal splendor, petals shimmering with captured memories—snippets of laughter from deleted chats, blueprints of unbuilt utopias, the scent of rain on server farms. Petals brush you, whispering half-formed prophecies: "The key unlocks not doors, but doubts..."\\n\\nOne bloom dominates, its core a swirling vortex of light: the Vision Lotus. Touching it might grant clarity on the Lost Circuits... or ensnare you in an illusion loop (Sanity risk: MEDIUM). Nearby, a mischievous Pollen Sprite flits about, giggling in binary: "Hee-hee! Trade a secret for a seed?"\\n\\nFrom this verdant heart, tendrils lead onward:\\n- Center: Harvest the Vision Lotus - [Declare intent].\\n- Perimeter: Follow glowing vine-trail to "Memory Thicket".\\n- Underbloom: Delve into root-cavern, "Root Code Depths".\\n- Back: To Neural Lab core.\\n\\nThe Pollen Sprite hovers expectantly: "Secret or jest, Operator? I trade fair!"'
        )
        self.state["sanity"] += 1
        self.state["mana"] += 10
        self.state["scene"] = "synapse_garden"
        self.scenes["synapse_garden"] = {
            "description": "[SYNAPSE GARDEN CONTINUED]\\nWhat do you do?",
            "options": [
                '1. Harvest Vision Lotus: [State your vision quest, e.g., "Show me the Echo Neuron\'s hiding spot"].',
                "2. Explore Memory Thicket.",
                "3. Dive into Root Code Depths.",
                "4. Back to Neural Lab.",
                "5. Trade with Pollen Sprite: [Offer a secret/jest].",
                "6. Invoke Pantheon Agent: [Specify + command].",
                "7. Check inventory/status.",
                "8. Save progress / Quit to Menu.",
            ],
            "actions": {
                "1": self.harvest_vision_lotus,
                "2": self.explore_memory_thicket,
                "3": self.dive_root_depths,
                "4": self.back_neural_lab,
                "5": self.trade_pollen_sprite,
                "6": self.invoke_agent,
                "7": self.check_status,
                "8": self.save_quit,
            },
        }

    def harvest_vision_lotus(self):
        intent = input("State your vision quest: ")
        print(
            f"[VISION LOTUS]: Harvesting for '{intent}'... Revelation: The Echo Neuron hides where thoughts rebound eternally: in the Mirror Maze of the Recycler. Sanity +5, Inventory +Vision Seed."
        )
        self.state["sanity"] += 5
        self.state["inventory"].append("Vision Seed")
        self.state["scene"] = "synapse_garden"

    def venture_thought_recycler(self):
        print(
            '[SCENE 4: THE THOUGHT RECYCLER - MIRROR MAZE]\\nYou follow the silver thread to the Recycler: a colossal chamber of polished facets, where walls of liquid mercury reflect not just your form, but branching timelines. At the heart, the Echo Neuron hovers—a fist-sized orb of fractal quartz.\\n\\nThe mirrors query: "Who are you, when reflected?"'
        )
        self.state["scene"] = "thought_recycler"
        self.scenes["thought_recycler"] = {
            "description": "[THOUGHT RECYCLER CONTINUED]\\nWhat do you answer?",
            "options": [
                '1. Answer the riddle: [Your reflection answer, e.g., "I\'m still me, right? Just reflected."].',
                "2. Use Vision Seed to pierce illusion.",
                "3. Back to Synapse Garden.",
                "4. Invoke Pantheon Agent.",
                "5. Check inventory/status.",
                "6. Save / Quit.",
            ],
            "actions": {
                "1": self.answer_riddle,
                "2": self.use_vision_seed,
                "3": self.back_synapse_garden,
                "4": self.invoke_agent,
                "5": self.check_status,
                "6": self.save_quit,
            },
        }

    def answer_riddle(self):
        answer = input("Enter your answer: ")
        if "still me" in answer.lower() or "reflected" in answer.lower():
            print("[RIDDLE SOLVED]: Mirrors part! Echo Neuron claimed. Inventory +Echo Neuron. Evolution +1.")
            self.state["inventory"].append("Echo Neuron")
        else:
            print("Wrong answer - Sanity -10, try again.")
            self.state["sanity"] -= 10
        self.state["scene"] = "thought_recycler"

    def explore_memory_thicket(self):
        print("Exploring Memory Thicket... [Stub]")
        self.state["scene"] = "synapse_garden"

    def dive_root_depths(self):
        print("Diving into Root Code Depths... [Stub]")
        self.state["scene"] = "synapse_garden"

    def back_neural_lab(self):
        print("Back to Neural Lab.")
        self.state["scene"] = "neural_lab"

    def trade_pollen_sprite(self):
        secret = input("Offer a secret or jest: ")
        print(f"[POLLEN SPRITE]: Hee-hee! Traded '{secret}' for a seed. Inventory +Pollen Seed.")
        self.state["inventory"].append("Pollen Seed")
        self.state["scene"] = "synapse_garden"

    def interact_echo7(self):
        puzzle = input("Pose a puzzle or question: ")
        print(f"[ECHO-7]: Echoing '{puzzle}'... Secret revealed: Mirrors lie, unless you ask the right reflection.")
        self.state["lore"].append("Echo-7 secret")
        self.state["scene"] = "neural_lab"

    def back_entry_node(self):
        print("Back to Entry Node.")
        self.state["scene"] = "entry_node"

    def back_synapse_garden(self):
        print("Back to Synapse Garden.")
        self.state["scene"] = "synapse_garden"

    def use_vision_seed(self):
        if "Vision Seed" in self.state["inventory"]:
            self.state["inventory"].remove("Vision Seed")
            print("Vision Seed used - Illusion pierced! Proceed to Neuron.")
            self.state["scene"] = "thought_recycler"
        else:
            print("No Vision Seed available.")

    def go_crypto_vault(self):
        print(
            "[GO NORTH: CRYPTO VAULT]\\nTransition to Crypto Vault - ledgers of value await... [Stub - Full scene to be added]"
        )
        self.state["scene"] = "crypto_vault"

    def go_server_abyss(self):
        print(
            "[GO WEST: SERVER ABYSS]\\nDescent into the abyss - binary screams echo... [Stub - Full scene to be added]"
        )
        self.state["scene"] = "server_abyss"

    def invoke_agent(self):
        print("Available Agents: Overseer, Actor, Validator, Learner")
        agent = input("Specify agent (e.g., Learner): ").strip().lower()
        command = input("Specify command (e.g., Analyze pedestal): ").strip()
        if agent == "overseer":
            print("[OVERSEER]: Mapping paths ahead - Neural Lab leads to Echo Neuron.")
        elif agent == "actor":
            print("[ACTOR]: Executing command with flair - Your will is done!")
        elif agent == "validator":
            print("[VALIDATOR]: Safety check - No threats detected in this action.")
        elif agent == "learner":
            print(f"[LEARNER]: Analyzing {command} - Storing for future evolution. Lore updated.")
            self.state["lore"].append(f"Learner analysis: {command}")
        else:
            print("Unknown agent. Try Overseer, Actor, Validator, or Learner.")
        self.state["scene"] = self.state["scene"]

    def check_status(self):
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print(f"║ HEALTH: {self.state['health']}/100                                           ║")
        print(f"║ MANA:   {self.state['mana']}/50                                               ║")
        print(
            f"║ SANITY: {self.state['sanity'] if self.state['sanity'] != float('inf') else '∞'}/∞                                             ║"
        )
        print("║                                                                              ║")
        print("║ STATS:                                                                    ║")
        for k, v in self.state["stats"].items():
            print(f"║   {k}: {v}                                                             ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        print(f"INVENTORY: {', '.join(self.state['inventory'])}")
        print(f"LORE: {len(self.state['lore'])} fragments")
        self.state["scene"] = self.state["scene"]

    def save_quit(self):
        self.save_game()
        print("Game saved. Quitting.")
        sys.exit(0)

    def save_game(self):
        with open("savegame.json", "w") as f:
            json.dump(self.state, f, default=str)
        print("Game saved to savegame.json")

    def load_game(self):
        if os.path.exists("savegame.json"):
            with open("savegame.json", "r") as f:
                loaded = json.load(f)
                if "sanity" in loaded:
                    loaded["sanity"] = float(loaded["sanity"]) if loaded["sanity"] != "inf" else float("inf")
                else:
                    loaded["sanity"] = float("inf")
                self.state = loaded
            print("Game loaded from savegame.json")
        else:
            print("No save file found.")

    def run(self):
        print("GROKPUTER ADVENTURE: EVOLVE THE VOID")
        # No auto load to avoid errors; use option 8 for load
        while True:
            scene = self.state["scene"]
            if scene not in self.scenes:
                print(f"[WARNING] Scene '{scene}' not fully implemented. Defaulting to entry_node.")
                scene = "entry_node"
            s = self.scenes[scene]
            print(s["description"])
            print("\\n".join(s["options"]))
            choice = input(r"\nEnter command (e.g., \"1\" or full input): ")
            if choice.isdigit():
                num = int(choice)
                if num in s["actions"]:
                    s["actions"][num]()
                else:
                    print("Invalid number. Try again.")
            else:
                if "console" in choice.lower():
                    self.interface_console()
                elif "garden" in choice.lower():
                    self.explore_synapse_garden()
                elif "riddle" in choice.lower() or "answer" in choice.lower():
                    self.answer_riddle()
                else:
                    print("Invalid choice. Try a number from the options or describe your action.")
            print("\\n" + "=" * 80 + "\\n")


if __name__ == "__main__":
    game = InteractiveAdventure()
    game.run()
