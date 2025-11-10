import sys
from pathlib import Path

with open('autonomous.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Insert functions after _improve's await line, before # Helper functions
insert_pos = -1
for i, line in enumerate(lines):
    if 'await _scan(target, category, severity, None, auto_propose=True, dangerously_skip_permissions=dangerously_skip_permissions)' in line:
        insert_pos = i + 1
        break

if insert_pos != -1:
    evolve_params = '''async def evolve_params(agent: str, chance: float):
    await asyncio.sleep(0.1)  # Yield for concurrency
    if random.random() < chance:
        # Mock param tweak logic
        return f"{agent} evolved: +0.1 divergence"
    return f"{agent} stable"
'''

    security_scan = '''async def security_scan(agent: str, target_path, scanner):
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
'''

    generate_haiku = '''async def generate_haiku(results):
    # Simple mock haiku; can integrate LLM later
    return "Eternal queues / Agents dance without wait / Bloom in code's night"
'''

    async_daemon_cycle = '''async def async_daemon_cycle(target_path, agents: List[str], chance: float = 0.3, r = None, scanner = None):
    """Async param evolution + security scan — non-blocking swarm bliss."""
    tasks = []
    for agent in agents:
        tasks.append(asyncio.create_task(evolve_params(agent, chance)))
        tasks.append(asyncio.create_task(security_scan(agent, target_path, scanner)))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    haiku = await generate_haiku(results)
    if r:
        r.set("eternal_bloom", haiku)
    console.print(f"Cycle complete: {len(results)} evals, {chance*100}% drift survived.")
    console.print(f"Haiku: {haiku}")
'''

    _daemon = '''async def _daemon(target: str, interval: int, evolve_chance: float, no_redis: bool):
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
        console.print("\n[green]Daemon stopped by user.[/green]")
        if r:
            r.set("daemon_stopped", "true")
'''

    new_functions = evolve_params + '\n\n' + security_scan + '\n\n' + generate_haiku + '\n\n' + async_daemon_cycle + '\n\n' + _daemon + '\n\n'
    lines.insert(insert_pos, new_functions)
    print('Functions inserted.')
else:
    print('Insert position not found.')

with open('autonomous.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('File updated successfully.')
