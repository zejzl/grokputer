import asyncio
from agent_framework import BaseAgent
import logging

logger = logging.getLogger(__name__)

class AlertManager(BaseAgent):
    def __init__(self, name: str, alert_file: str = "alerts.log", email_sim: bool = False):
        super().__init__(name)
        self.alert_file = alert_file
        self.email_sim = email_sim
        self.shared_queue = None  # To be set by manager

    async def run(self):
        self.running = True
        while self.running:
            if self.shared_queue:
                try:
                    msg = await self.shared_queue.get_nowait()
                    self.handle_alert(msg)
                except asyncio.QueueEmpty:
                    pass
            await asyncio.sleep(1)

    def handle_alert(self, msg):
        alert_type = msg.get("type", "unknown")
        if alert_type == "analytics_alert":
            print(f"🚨 ALERT: High analytics activity - {msg['data']}")
            logger.warning(f"Analytics Alert: {msg['data']}")
        elif alert_type == "security_breach":
            print(f"🔒 SECURITY BREACH: {msg['input']}")
            logger.error(f"Security Breach: {msg['input']}")
        elif alert_type == "perf_alert":
            print(f"[FAST] PERFORMANCE ISSUE: CPU {msg['cpu']}%, MEM {msg['mem']}%")
            logger.warning(f"Perf Alert: CPU {msg['cpu']}, MEM {msg['mem']}")
        # Simulate email
        if self.email_sim:
            print(f"📧 Simulated email sent for {alert_type}")
        # Log to file
        with open(self.alert_file, "a") as f:
            f.write(f"{time.asctime()}: {alert_type} - {msg}\n")