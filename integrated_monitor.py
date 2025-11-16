import logging
import time
import asyncio
from collections import defaultdict
from agent_framework import AgentManager
from monitoring_agents import LogMonitor, AnalyticsWatcher, SecurityAgent, PerformanceMonitor
from security_utils import check_input as orig_check_input, validate_input  # Assuming check_input is simple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Analytics
analytics = defaultdict(int)

def log_event(event):
    logger.info(f"Event: {event}")
    analytics[event] += 1

def get_analytics():
    return dict(analytics)

# Enhanced check with validation
def check_input(user_input):
    if orig_check_input(user_input) and validate_input(user_input):
        return True
    log_event("Invalid input detected")
    return False

async def run_system():
    manager = AgentManager()
    manager.add_agent(LogMonitor("log_monitor"))
    manager.add_agent(AnalyticsWatcher("analytics_watcher"))
    manager.add_agent(SecurityAgent("security_agent"))
    manager.add_agent(PerformanceMonitor("perf_monitor"))
    
    agent_task = asyncio.create_task(manager.start_all())
    
    log_event("Integrated system started")
    while True:
        user_input = input("Enter command: ")
        if check_input(user_input):
            log_event(f"Processed: {user_input}")
        else:
            log_event("Input rejected")
        print("Analytics:", get_analytics())
        await asyncio.sleep(1)
    
    await agent_task

if __name__ == "__main__":
    asyncio.run(run_system())