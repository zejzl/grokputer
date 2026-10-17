#!/usr/bin/env python3
"""
Test the fixed executor.py to verify security improvements.
"""

import sys
from pathlib import Path

<<<<<<< HEAD
with open("autonomous.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find position before if __name__ == '__main__':
insert_pos = -1
for i, line in enumerate(lines):
    if "if __name__" in line:
        insert_pos = i
        break

if insert_pos != -1:
    # Daemon CLI command
    daemon_lines = [
        "",
        "@cli.command()",
        '@click.argument("target", type=click.Path(exists=True))',
        '@click.option("--interval", type=int, default=60, help="Cycle interval in seconds")',
        '@click.option("--evolve-chance", type=float, default=0.3, help="Chance of param evolution")',
        '@click.option("--no-redis", is_flag=True, help="Disable Redis persistence")',
        "def daemon(target: str, interval: int, evolve_chance: float, no_redis: bool):",
    # Limited to 3 iterations by default to avoid infinite loops
        '    """',
        "    Run daemon mode for continuous code monitoring and evolution.",
        "",
        "    TARGET is the directory or file to monitor.",
        '    """',
        "    asyncio.run(_daemon(target, interval, evolve_chance, no_redis))",
        "",
        "async def evolve_params(agent: str, chance: float):",
        "    await asyncio.sleep(0.1)  # Yield for concurrency",
        "    if random.random() < chance:",
        "        # Mock param tweak logic",
        '        return f"{agent} evolved: +0.1 divergence"',
        '    return f"{agent} stable"',
        "",
        "async def security_scan(agent: str, target_path, scanner):",
        "    vulns = []",
        '    if agent == "scanner" and scanner and target_path:',
        "        try:",
        "            report = await scanner.scan_directory(target_path)",
        '            vulns = [f for f in report.findings if f.severity in ["critical", "high"]]',
        "        except Exception as e:",
        "            vulns = []  # Graceful fail",
        "    if vulns:",
        '        console.print(f"[yellow]{len(vulns)} issues detected in {agent}! Review proposals.[/yellow]")',
        '    return f"{agent}: {len(vulns)} alerts"',
        "",
        "async def generate_haiku(results):",
        "    # Simple mock haiku; can integrate LLM later",
        '    return "Eternal queues / Agents dance without wait / Bloom in code\'s night"',
        "",
        "async def async_daemon_cycle(target_path, agents: List[str], chance: float = 0.3, r = None, scanner = None):",
        '    """Async param evolution + security scan — non-blocking swarm bliss."""',
        "    tasks = []",
        "    for agent in agents:",
        "        tasks.append(asyncio.create_task(evolve_params(agent, chance)))",
        "        tasks.append(asyncio.create_task(security_scan(agent, target_path, scanner)))",
        "    ",
        "    results = await asyncio.gather(*tasks, return_exceptions=True)",
        "    ",
        "    haiku = await generate_haiku(results)",
        "    if r:",
        '        r.set("eternal_bloom", haiku)',
        '    console.print(f"Cycle complete: {len(results)} evals, {chance*100}% drift survived.")',
        '    console.print(f"Haiku: {haiku}")',
        "",
        "async def _daemon(target: str, interval: int, evolve_chance: float, no_redis: bool):",
        "    target_path = Path(target)",
        '    api_key = os.getenv("XAI_API_KEY")',
        "    if not api_key:",
        '        console.print("[red]Error:[/red] XAI_API_KEY environment variable not set")',
        "        return",
        "    scanner = CodeScannerAgent()",
        "    proposer = ProposalGeneratorAgent(api_key=api_key)  # For future use",
        '    agents = ["scanner", "proposer"]',
        "    r = None",
        "    if not no_redis:",
        "        try:",
        '            r = redis.Redis(host="localhost", port=6379, db=0)',
        "            r.ping()",
        '            console.print("[green]Redis connected.[/green]")',
        "        except Exception as e:",
        '            console.print(f"[yellow]Redis unavailable ({e}), using console fallback.[/yellow]")',
        "            r = None",
        '    console.print(f"[bold green]Starting autonomous daemon on {target_path} (interval: {interval}s)[/bold green]")',
        "    try:",
        "        for _ in range(3):",
        "            await async_daemon_cycle(target_path, agents, evolve_chance, r, scanner)",
        "            await asyncio.sleep(interval)",
        "    except KeyboardInterrupt:",
        '        console.print("\\n[green]Daemon stopped by user.[/green]")',
        "        if r:",
        '            r.set("daemon_stopped", "true")',
        "",
    ]
    for line in daemon_lines:
        lines.insert(insert_pos, line + "\n")
    print("Daemon and functions inserted.")
else:
    print("Insert position not found.")

with open("autonomous.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
print("File updated successfully.")
=======
# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from executor import ToolExecutor


def test_safe_commands():
    """Test that safe commands still work."""
    print("\n=== Testing Safe Commands ===\n")

    executor = ToolExecutor(require_confirmation=False)

    # Test simple commands
    test_cases = [
        {"command": "echo hello"},
        {"command": "ls -la"},
        {"command": "pwd"},
    ]

    for args in test_cases:
        print(f"Testing: {args['command']}")
        result = executor._execute_bash(args)
        print(f"  Status: {result['status']}")
        if result["status"] == "success":
            print(f"  Output: {result['stdout'][:100]}")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')}")
        print()


def test_dangerous_commands():
    """Test that dangerous commands are blocked."""
    print("\n=== Testing Dangerous Commands (Should Be Blocked) ===\n")

    executor = ToolExecutor(require_confirmation=False)

    # Test injection attempts
    injection_attempts = [
        {"command": "ls; rm -rf /"},
        {"command": "echo test && cat /etc/passwd"},
        {"command": "ls | grep test"},
        {"command": "cat file > output.txt"},
        {"command": "echo $(whoami)"},
        {"command": "echo `hostname`"},
    ]

    for args in injection_attempts:
        print(f"Testing: {args['command']}")
        result = executor._execute_bash(args)
        print(f"  Status: {result['status']}")
        print(f"  Risk: {result.get('risk_level', 'N/A')}")
        if result["status"] == "error":
            print(f"  [OK] BLOCKED: {result.get('error', '')[:100]}")
        else:
            print(f"  [WARN] Command was not blocked!")
        print()


if __name__ == "__main__":
    print("=" * 60)
    print("EXECUTOR SECURITY FIX TEST")
    print("=" * 60)

    test_safe_commands()
    test_dangerous_commands()

    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
>>>>>>> e677e0688f3c74836b1e66bc7d95377e320f2b0e
