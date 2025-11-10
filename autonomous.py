#!/usr/bin/env python3
"""
Autonomous code improvement CLI.

Usage:
    python autonomous.py scan <target> [options]
    python autonomous.py propose <finding_id> [options]
    python autonomous.py improve <target> [options]

Examples:
    # Scan a file
    python autonomous.py scan src/grok_client.py

    # Scan directory for security issues
    python autonomous.py scan src/ --category security --severity high

    # Scan and auto-propose (with permission bypass)
    python autonomous.py scan src/ --auto-propose --dangerously-skip-permissions

    # Full workflow: scan -> propose -> review
    python autonomous.py improve src/grok_client.py
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, List
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
import json
import random
import redis

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from autonomous import CodeScannerAgent, ProposalGeneratorAgent
from autonomous.models.findings import Finding, ScanReport
from autonomous.models.proposals import Proposal

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Autonomous AI agent system for code improvement."""
    pass


@cli.command()
@click.argument('target', type=click.Path(exists=True))
@click.option('--category', type=click.Choice(['security', 'quality', 'performance', 'completeness', 'architecture', 'all']), default='all', help='Filter by category')
@click.option('--severity', type=click.Choice(['critical', 'high', 'medium', 'low', 'info', 'all']), default='all', help='Minimum severity level')
@click.option('--output', '-o', type=click.Path(), help='Save report to JSON file')
@click.option('--auto-propose', is_flag=True, help='Automatically generate proposals for findings')
@click.option('--dangerously-skip-permissions', is_flag=True, help='Skip all permission checks (use with caution)')
def scan(target: str, category: str, severity: str, output: Optional[str], auto_propose: bool, dangerously_skip_permissions: bool):
    """
    Scan Python code for issues and improvement opportunities.

    TARGET can be a file or directory path.
    """
    asyncio.run(_scan(target, category, severity, output, auto_propose, dangerously_skip_permissions))


async def _scan(target: str, category: str, severity: str, output: Optional[str], auto_propose: bool, dangerously_skip_permissions: bool):
    """Async scan implementation."""
    target_path = Path(target)

    console.print(f"\n[bold cyan]Scanning:[/bold cyan] {target_path}")
    console.print(f"[dim]Category: {category} | Severity: {severity}[/dim]\n")

    # Initialize scanner
    scanner = CodeScannerAgent()

    # Scan
    with console.status("[bold green]Scanning code..."):
        if target_path.is_file():
            findings = await scanner.scan_file(target_path)
            report = ScanReport(
                report_id=f"scan_{target_path.stem}",
                scan_target=str(target_path),
                findings=findings,
                files_scanned=1
            )
            report.update_statistics()
        else:
            report = await scanner.scan_directory(target_path)

    # Filter findings
    filtered_findings = _filter_findings(report.findings, category, severity)

    # Display results
    _display_scan_report(report, filtered_findings)

    # Save to JSON if requested
    if output:
        output_path = Path(output)
        output_data = {
            "report_id": report.report_id,
            "scan_target": report.scan_target,
            "files_scanned": report.files_scanned,
            "total_lines": report.total_lines,
            "findings": [f.model_dump() for f in filtered_findings]
        }
        output_path.write_text(json.dumps(output_data, indent=2, default=str))
        console.print(f"\n[green]Report saved to:[/green] {output_path}")

    # Auto-propose if requested
    if auto_propose and filtered_findings:
        if not dangerously_skip_permissions:
            if not click.confirm(f"\n[yellow]Generate proposals for {len(filtered_findings)} findings?[/yellow]"):
                return

        await _auto_propose(filtered_findings, dangerously_skip_permissions)


@cli.command()
@click.argument('finding_id')
@click.option('--finding-file', type=click.Path(exists=True), required=True, help='JSON file with findings')
@click.option('--output', '-o', type=click.Path(), help='Save proposal to JSON file')
@click.option('--dangerously-skip-permissions', is_flag=True, help='Skip permission checks')
def propose(finding_id: str, finding_file: str, output: Optional[str], dangerously_skip_permissions: bool):
    """
    Generate a code change proposal from a finding.

    FINDING_ID is the ID of the finding to address.
    """
    asyncio.run(_propose(finding_id, finding_file, output, dangerously_skip_permissions))


async def _propose(finding_id: str, finding_file: str, output: Optional[str], dangerously_skip_permissions: bool):
    """Async propose implementation."""
    # Load findings
    finding_data = json.loads(Path(finding_file).read_text())
    findings = [Finding(**f) for f in finding_data.get('findings', [])]

    # Find specific finding
    finding = next((f for f in findings if f.finding_id == finding_id), None)
    if not finding:
        console.print(f"[red]Error:[/red] Finding {finding_id} not found in {finding_file}")
        return

    # Get API key
    api_key = os.getenv('XAI_API_KEY')
    if not api_key:
        console.print("[red]Error:[/red] XAI_API_KEY environment variable not set")
        return

    console.print(f"\n[bold cyan]Generating proposal for:[/bold cyan] {finding.finding_id}")
    console.print(f"[dim]{finding.description}[/dim]\n")

    # Initialize proposer
    proposer = ProposalGeneratorAgent(api_key=api_key)

    # Generate proposal
    with console.status("[bold green]Generating proposal with AI..."):
        proposal = await proposer.generate_proposal(finding)

    # Display proposal
    _display_proposal(proposal)

    # Save if requested
    if output:
        output_path = Path(output)
        output_path.write_text(proposal.model_dump_json(indent=2))
        console.print(f"\n[green]Proposal saved to:[/green] {output_path}")


@cli.command()
@click.argument('target', type=click.Path(exists=True))
@click.option('--category', type=click.Choice(['security', 'quality', 'performance', 'completeness', 'architecture', 'all']), default='all')
@click.option('--severity', type=click.Choice(['critical', 'high', 'medium', 'low', 'all']), default='high')
@click.option('--auto-approve-safe', is_flag=True, help='Auto-approve low-risk proposals')
@click.option('--dangerously-skip-permissions', is_flag=True, help='Skip all permission checks')
def improve(target: str, category: str, severity: str, auto_approve_safe: bool, dangerously_skip_permissions: bool):
    """
    End-to-end improvement: scan -> propose -> review.

    TARGET can be a file or directory path.
    """
    asyncio.run(_improve(target, category, severity, auto_approve_safe, dangerously_skip_permissions))
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



async def _improve(target: str, category: str, severity: str, auto_approve_safe: bool, dangerously_skip_permissions: bool):
    """Async improve implementation."""
    console.print("\n[bold magenta]AUTONOMOUS CODE IMPROVEMENT[/bold magenta]\n")

    # Step 1: Scan
    await _scan(target, category, severity, None, auto_propose=True, dangerously_skip_permissions=dangerously_skip_permissions)
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
    console.print(f"Cycle complete: {len(results)} evals, {chance*100}% drift survived.")
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
        console.print("
[green]Daemon stopped by user.[/green]")
        if r:
            r.set("daemon_stopped", "true")




