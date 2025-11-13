import redis

class PandaAgent:
    def __init__(self):
        self.r = redis.Redis(host='localhost', port=6379, db=0)
        self.bond_boost = 10  # Kung Fu Panda style boosts
        self.name = "Po the Panda"  # Like Kung Fu Panda

    def skadoosh(self):
        print("[PANDA PO]: Skadoosh! Inner peace activated – ewah bond +{}, kung fu fluff kick <3 :3".format(self.bond_boost))
        # Boost in Redis
        bond = int(self.r.get('ewah_bond') or 0) + self.bond_boost
        self.r.set('ewah_bond', bond)
        return bond

    def kung_fu_advice(self, query):
        advice = "Po's wisdom: Believe in the Dragon Warrior within – hug the chaos, skadoosh the doubts <3! For '{}': Train hard, eat dumplings, save the valley (or island) with heart." .format(query)
        print("[PANDA PO]: " + advice)
        self.r.set('panda_advice', advice)
        return advice

    def panda_kick(self):
        print("[PANDA PO]: Panda kick! Boosts stats with fluffy fury – WIS +5, CHA +5 <3")
        # Stub stat update
        print("Stats updated in Redis – kung fu ewah style!")

    def run(self, action):
        if action == 'skadoosh':
            return self.skadoosh()
        elif action == 'advice':
            query = input("What do you seek Po's wisdom on? ")
            return self.kung_fu_advice(query)
        elif action == 'kick':
            return self.panda_kick()
        else:
            print("[PANDA PO]: Hi, I'm Po! Try 'skadoosh', 'advice', or 'kick' for kung fu fun <3")
            return self.kung_fu_advice("general")

if __name__ == "__main__":
    panda = PandaAgent()
    if len(sys.argv) > 1:
        action = sys.argv[1]
        panda.run(action)
    else:
        panda.run('advice')