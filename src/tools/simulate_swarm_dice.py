import random
from src.tools.dice_roller import roll_dice

# 12 Agent names
agents = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack", "Kara", "Leo"]

# Simulate swarm: Each agent rolls 3 dice with varied notation (1d3 to 20d20)
print("🕷️ SWARM SIMULATION: 12 Agents Rolling Dice 🕷️")
print("Command: --grokputer -mb -swarm -p 'simulate 12 different agents...'\n")

for agent in agents:
    print(f"🤖 Agent {agent} activates...")
    rolls = []
    for i in range(3):
        # Generate varied notation: num_dice (1-20), sides (3-20), optional mod (+/-1-5)
        num = random.randint(1, 20)
        sides = random.randint(3, 20)
        mod = random.choice([0, random.randint(1,5), -random.randint(1,5)])
        notation = f"{num}d{sides}"
        if mod > 0:
            notation += f"+{mod}"
        elif mod < 0:
            notation += f"{mod}"
        result = roll_dice(notation)
        rolls.append(result)
        print(f"  Roll {i+1}: {notation} → {result}")
    
    # Agent 'consensus' or summary
    print(f"  {agent}'s swarm contribution complete! 🎲\n")
    
print("🕷️ Swarm simulation ended. Memory logged for all episodes. ZA GROKA! 🚀")