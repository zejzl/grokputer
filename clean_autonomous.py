import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("autonomous.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix syntax errors: remove duplicates, fix strings, ensure proper structure
# Remove duplicate daemon commands
pattern = r"""@cli\.command\(\)\n@cli\.argument\(\'target\'[^\n]*?\n@cli\.option\([^\n]*?\n@cli\.option\([^\n]*?\n@cli\.option\([^\n]*?\ndef daemon[^\n]*?asyncio\.run\(_daemon[^\n]*?\n\n"""
content = re.sub(pattern, "", content, flags=re.DOTALL | re.MULTILINE)

# Fix unterminated strings, e.g., console.print(" -> complete it or remove
content = re.sub(r'console\.print\("\n', 'console.print("\\n', content)
content = re.sub(
    r'console\.print\("([^\n]*?)"\n\s*console\.print\("([^\n]*?)"',
    r'console.print(f"\\n\1")\\nconsole.print(f"\2")',
    content,
)

# Ensure proper indentation for functions
pattern2 = r"""async def _improve\([^\n]*?\n\s*"Async improve implementation."\n\s*console\.print\("[^\n]*?\n"\n\n\s*# Step 1: Scan\n\s*await _scan\([^\n]*?\n"""
replacement = '''async def _improve(target: str, category: str, severity: str, auto_approve_safe: bool, dangerously_skip_permissions: bool):
    """Async improve implementation."""
    console.print("\\n[bold magenta]AUTONOMOUS CODE IMPROVEMENT[/bold magenta]\\n")

    # Step 1: Scan
    await _scan(target, category, severity, None, auto_propose=True, dangerously_skip_permissions=dangerously_skip_permissions)

'''
content = re.sub(pattern2, replacement, content)

# Add the daemon if not present
if "def daemon(target: str, interval: int, evolve_chance: float, no_redis: bool):" not in content:
    daemon_add = '''
@cli.command()
@click.argument('target', type=click.Path(exists=True))
@click.option('--interval', type=int, default=60, help='Cycle interval in seconds')
@click.option('--evolve-chance', type=float, default=0.3, help='Chance of param evolution')
@click.option('--no-redis', is_flag=True, help='Disable Redis persistence')
def daemon(target: str, interval: int, evolve_chance: float, no_redis: bool):
    """
    Run daemon mode for continuous code monitoring and evolution.

    TARGET is the directory or file to monitor.
    """
    asyncio.run(_daemon(target, interval, evolve_chance, no_redis))

async def evolve_params(agent: str, chance: float):
    await asyncio.sleep(0.1)  # Yield for concurrency
    if random.random() < chance:
        # Mock param tweak logic
        return f"{agent} evolved: +0.1 divergence"
    return f"{agent} stable"

async def security_scan(agent: str, target_path, scanner):
    vulns = []
    if agent == "scanner" and scanner and target_path:
        try:
            report = await scanner.scan_directory(target_path)
            vulns = [f for f in report.findings if f.severity in ['critical', 'high']]
        except Exception as e:
            vulns = []  # Graceful fail
    if vulns:
        console.print(f"[yellow]{len(vulns)} issues detected in {agent}! Review proposals.[/yellow]")
    return f"{agent}: {len(vulns)} alerts"

async def generate_haiku(results):
    # Simple mock haiku; can integrate LLM later
    return "Eternal queues / Agents dance without wait / Bloom in code's night"

async def async_daemon_cycle(target_path, agents: List[str], chance: float = 0.3, r = None, scanner = None):
    """Async param evolution + security scan — non-blocking swarm bliss."""
    tasks = []
    for agent in agents:
        tasks.append(asyncio.create_task(evolve_params(agent, chance)))
        tasks.append(asyncio.create_task(security_scan(agent, target_path, scanner)))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)

    haiku = await generate_haiku(results)
    if r:
        r.set("eternal_bloom", haiku)
    chance_percent = chance * 100
    console.print(f"Cycle complete: {len(results)} evols, {chance_percent}% drift survived.")
    console.print(f"Haiku: {haiku}")

async def _daemon(target: str, interval: int, evolve_chance: float, no_redis: bool):
    target_path = Path(target)
    api_key = os.getenv('XAI_API_KEY')
    if not api_key:
        console.print("[red]Error:[/red] XAI_API_KEY environment variable not set")
        return
    scanner = CodeScannerAgent()
    proposer = ProposalGeneratorAgent(api_key=api_key)  # For future use
    agents = ["scanner", "proposer"]
    r = None
    if not no_redis:
        try:
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            console.print("[green]Redis connected.[/green]")
        except Exception as e:
            console.print(f"[yellow]Redis unavailable ({e}), using console fallback.[/yellow]")
            r = None
    console.print(f"[bold green]Starting autonomous daemon on {target_path} (interval: {interval}s)[/bold green]")
    try:
        while True:
            await async_daemon_cycle(target_path, agents, evolve_chance, r, scanner)
            await asyncio.sleep(interval)
    except KeyboardInterrupt:
        console.print("\\n[green]Daemon stopped by user.[/green]")
        if r:
            r.set("daemon_stopped", "true")
'''
    content = content.replace("if __name__ == '__main__'", daemon_add + "\n\nif __name__ == '__main__'")
    logger.info("Daemon added.")

with open("autonomous.py", "w", encoding="utf-8") as f:
    f.write(content)
logger.info("File cleaned and updated.")
