with open('src/agents/pantheon_coordinator.py', 'r', encoding='utf-8') as f: content = f.read()

# Add backoff/retry to message sending
import_pattern = 'import asyncio'
if import_pattern in content:
    content = content.replace(import_pattern, import_pattern + '\nimport tenacity')

# Find send_message or similar, add retry
send_pattern = 'await self.message_bus.send('
if send_pattern in content:
    retry_decorator = '\n    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=1, max=10), stop=tenacity.stop_after_attempt(3))\n    async def _send_with_retry(self, to_agent, content):\n        return await self.message_bus.send(to_agent, content)\n'
    content = content.replace(send_pattern, retry_decorator + '        ' + send_pattern.replace('await self.message_bus.send', 'await self._send_with_retry'))

with open('src/agents/pantheon_coordinator.py', 'w', encoding='utf-8') as f: f.write(content)

print('Pantheon retry added')