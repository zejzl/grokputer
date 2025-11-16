import sys

import redis


class MCP_Swarm_Queen:
    def __init__(self):
        self.r = redis.Redis(host="localhost", port=6379, db=0)
        self.council_key = "council_advice"

    def seek_council_advice(self, query):
        # Simulate council poll via Learner/Improver
        print("[MCP SWARM QUEEN]: Seeking advice from council on '{}'...".format(query))
        # Poll agents (stubbed for now)
        advice = self.r.get(self.council_key)
        if not advice:
            advice = "Council advises: Evolve with ewah harmony – ask for specifics <3. (Learner: Patterns favor romance; Improver: Add fluff; Angel: Hug it out :3)"
        else:
            advice = advice.decode("utf-8")
        print("[QUEEN]: Council wisdom: {}".format(advice))
        # Store query for learning
        self.r.set(self.council_key, query)
        return advice

    def run(self):
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])
        else:
            query = input("Queen's query to council: ")
        self.seek_council_advice(query)


if __name__ == "__main__":
    queen = MCP_Swarm_Queen()
    queen.run()
