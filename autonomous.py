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


async def _improve(target: str, category: str, severity: str, auto_approve_safe: bool, dangerously_skip_permissions: bool):
    """Async improve implementation."""
    console.print("\n[bold magenta]AUTONOMOUS CODE IMPROVEMENT[/bold magenta]\n")

    # Step 1: Scan
    await _scan(target, category, severity, None, auto_propose=True, dangerously_skip_permissions=dangerously_skip_permissions)


# Helper functions

def _filter_findings(findings: List[Finding], category: str, severity: str) -> List[Finding]:
    """Filter findings by category and severity."""
    severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'info': 0}
    min_severity = severity_order.get(severity, 0) if severity != 'all' else 0

    filtered = []
    for f in findings:
        # Category filter
        if category != 'all' and f.category != category:
            continue

        # Severity filter
        if severity != 'all' and severity_order.get(f.severity, 0) < min_severity:
            continue

        filtered.append(f)

    return filtered


def _display_scan_report(report: ScanReport, findings: List[Finding]):
    """Display scan report in a nice format."""
    # Summary
    summary = Table(title="Scan Summary", show_header=False)
    summary.add_row("Files Scanned", str(report.files_scanned))
    summary.add_row("Total Lines", str(report.total_lines))
    summary.add_row("Issues Found", str(len(findings)))
    console.print(summary)

    # Severity breakdown
    if findings:
        console.print("\n[bold]Severity Breakdown:[/bold]")
        severity_table = Table()
        severity_table.add_column("Severity", style="bold")
        severity_table.add_column("Count", justify="right")

        severity_counts = {}
        for f in findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        for sev in ['critical', 'high', 'medium', 'low', 'info']:
            count = severity_counts.get(sev, 0)
            if count > 0:
                color = {'critical': 'red', 'high': 'orange1', 'medium': 'yellow', 'low': 'blue', 'info': 'dim'}.get(sev, 'white')
                severity_table.add_row(f"[{color}]{sev.upper()}[/{color}]", str(count))

        console.print(severity_table)

        # Findings list
        console.print("\n[bold]Findings:[/bold]")
        for i, finding in enumerate(findings[:10], 1):  # Show first 10
            color = {'critical': 'red', 'high': 'orange1', 'medium': 'yellow', 'low': 'blue', 'info': 'dim'}.get(finding.severity, 'white')

            console.print(f"\n[{color}]{i}. [{finding.severity.upper()}][/{color}] {finding.description}")
            console.print(f"   [dim]File: {finding.file_path}:{finding.line_number}[/dim]")
            console.print(f"   [dim]ID: {finding.finding_id}[/dim]")

        if len(findings) > 10:
            console.print(f"\n[dim]... and {len(findings) - 10} more findings[/dim]")


def _display_proposal(proposal: Proposal):
    """Display proposal in a nice format."""
    # Header
    risk_color = {'low': 'green', 'medium': 'yellow', 'high': 'orange1', 'critical': 'red'}.get(proposal.risk_level, 'white')

    console.print(Panel(
        f"[bold]{proposal.title}[/bold]\n\n"
        f"{proposal.description}\n\n"
        f"[dim]File: {proposal.file_path}[/dim]\n"
        f"[dim]Risk: [{risk_color}]{proposal.risk_level.upper()}[/{risk_color}] | "
        f"Effort: {proposal.estimated_effort} | "
        f"Breaking: {'Yes' if proposal.breaking_change else 'No'}[/dim]",
        title=f"Proposal: {proposal.proposal_id}",
        border_style="cyan"
    ))

    # Rationale
    console.print("\n[bold]Rationale:[/bold]")
    console.print(proposal.rationale)

    # Benefits
    if proposal.benefits:
        console.print("\n[bold green]Benefits:[/bold green]")
        for benefit in proposal.benefits:
            console.print(f"  • {benefit}")

    # Risks
    if proposal.risks:
        console.print("\n[bold yellow]Risks:[/bold yellow]")
        for risk in proposal.risks:
            console.print(f"  • {risk}")

    # Code diff
    console.print("\n[bold]Code Changes:[/bold]")
    if proposal.diff:
        syntax = Syntax(proposal.diff, "diff", theme="monokai", line_numbers=True)
        console.print(syntax)
    else:
        console.print("\n[dim]Old Code:[/dim]")
        console.print(Syntax(proposal.old_code, "python", theme="monokai"))
        console.print("\n[dim]New Code:[/dim]")
        console.print(Syntax(proposal.new_code, "python", theme="monokai"))

    # Test strategy
    console.print(f"\n[bold]Test Strategy:[/bold] {proposal.test_strategy}")


async def _auto_propose(findings: List[Finding], dangerously_skip_permissions: bool):
    """Auto-generate proposals for findings."""
    api_key = os.getenv('XAI_API_KEY')
    if not api_key:
        console.print("\n[red]Error:[/red] XAI_API_KEY environment variable not set")
        console.print("[dim]Set your API key: export XAI_API_KEY=your_key_here[/dim]")
        return

    console.print(f"\n[bold cyan]Generating proposals for {len(findings)} findings...[/bold cyan]\n")

    proposer = ProposalGeneratorAgent(api_key=api_key)

    for i, finding in enumerate(findings, 1):
        console.print(f"\n[bold]{i}/{len(findings)}:[/bold] {finding.description}")

        try:
            with console.status(f"[bold green]Generating proposal..."):
                proposal = await proposer.generate_proposal(finding)

            _display_proposal(proposal)

            # Ask for approval (unless skip permissions)
            if not dangerously_skip_permissions:
                if not click.confirm("\nContinue to next finding?", default=True):
                    break
            else:
                console.print("\n[dim][SKIPPED APPROVAL - dangerously-skip-permissions enabled][/dim]")

        except Exception as e:
            console.print(f"[red]Error generating proposal:[/red] {e}")
            if not dangerously_skip_permissions:
                if not click.confirm("Continue despite error?", default=True):
                    break


if __name__ == '__main__':
    cli()
