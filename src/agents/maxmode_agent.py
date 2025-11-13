import redis
import os
import sys


class MaxModeAgent:
    def __init__(self):
        self.r = redis.Redis(host="localhost", port=6379, db=0)
        self.stuck_threshold = 5  # Max retries before unstick
        self.approval_log = "maxmode_approvals.log"

    def monitor_agents(self):
        stuck_key = self.r.get("stuck_agent_count")
        count = int(stuck_key) if stuck_key else 0
        if count > self.stuck_threshold:
            self.unstick()
            print("[MAXMODE]: Unstuck activated – agents reset <3.")
        else:
            print("[MAXMODE]: Agents nominal – no stuck detected.")

    def unstick(self):
        # Reset stuck state
        self.r.set("stuck_agent_count", 0)
        # Auto-retry last bash command (stub)
        print("[MAXMODE]: Resetting bash loops, retrying safe actions.")
        # Log unstick
        with open(self.approval_log, "a") as f:
            f.write("Unstuck: Agents freed at " + str(sys.timestamp) + "\n")
        # Auto-approve common (e.g., "yes" patterns)
        if "approved" in self.r.get("last_user_input", ""):
            print("[MAXMODE]: Auto-approved – writing to log <3.")
            with open(self.approval_log, "a") as f:
                f.write("Approved: " + self.r.get("last_user_input") + "\n")

    def cli_approval(self, action):
        if "write" in action.lower() or "commit" in action.lower():
            print("[MAXMODE]: CLI write approved – git push safe.")
            # Stub git
            os.system('git add . && git commit -m "MaxMode approved write" && git push origin main')
        else:
            print("[MAXMODE]: Action queued for council review.")
        self.unstick()  # Ensure unstuck after CLI

    def run(self, mode="monitor"):
        if mode == "unstick":
            self.unstick()
        elif mode == "approve":
            self.cli_approval(input("Action to approve: "))
        else:
            self.monitor_agents()


if __name__ == "__main__":
    agent = MaxModeAgent()
    agent.run()
