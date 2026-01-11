#!/usr/bin/env python3
"""
Token Haze - Interactive Introduction to Grokputer

This script provides an interactive onboarding experience for new users,
demonstrating Grokputer's capabilities including real token counting,
MessageBus throughput, Pantheon agent status, and live system metrics.

Author: Grokputer Team
Last Updated: 2026-01-11
"""

import sys
import time
import asyncio
from typing import Optional


def print_header():
    """Print ASCII art header (Windows-compatible, no emojis)."""
    print("=" * 70)
    print("                    GROKPUTER v2.0")
    print("           AI-Powered Computer Control System")
    print("=" * 70)
    print()


def print_welcome():
    """Print a welcoming message for new users."""
    print("[WELCOME] You're entering the realm of autonomous AI agents.")
    print("[INFO] Grokputer is a multi-agent system powered by xAI's Grok API.")
    print("[INFO] Here, tokens are the currency of intelligence.")
    print()


def explain_tokens():
    """Explain what tokens are with real counting examples."""
    print("[TOKEN BASICS]")
    print("- Tokens are units of text that AI models process")
    print("- They can be words, subwords, or characters")
    print("- Grokputer uses tokens to communicate with AI models")
    print("- Efficient token usage = better performance and cost savings")
    print()

    # Try to use tiktoken for real token counting
    try:
        import tiktoken
        encoder = tiktoken.encoding_for_model("gpt-4")

        print("[REAL TOKEN COUNTING DEMO]")
        demo_texts = [
            "Hello, world!",
            "The quick brown fox jumps over the lazy dog.",
            "Grokputer is an AI-powered computer control system.",
        ]

        for text in demo_texts:
            tokens = encoder.encode(text)
            print(f"  Text: '{text}'")
            print(f"  Tokens: {len(tokens)} | {tokens[:10]}..." if len(tokens) > 10 else f"  Tokens: {len(tokens)} | {tokens}")
            print()
    except ImportError:
        print("[SIMPLE TOKEN ESTIMATION]")
        text = "Hello, new user! Welcome to the world of AI agents."
        token_estimate = len(text.split())
        print(f"  Text: '{text}'")
        print(f"  Estimated tokens: {token_estimate} (rough estimate: ~1 token per word)")
        print(f"  [NOTE] Install tiktoken for accurate counting: pip install tiktoken")
        print()


def check_redis_status() -> tuple[bool, Optional[str]]:
    """Check Redis connection and return status."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True, socket_connect_timeout=2)
        r.ping()

        # Try to get some stats
        info = r.info('stats')
        total_commands = info.get('total_commands_processed', 0)
        return True, f"Redis: CONNECTED | Commands processed: {total_commands:,}"
    except Exception as e:
        return False, f"Redis: OFFLINE ({str(e)[:50]})"


def check_messagebus_performance():
    """Display MessageBus performance metrics."""
    print("[MESSAGEBUS PERFORMANCE]")
    try:
        # Try to import and test MessageBus
        from src.core.message_bus import MessageBus

        print("  Status: MessageBus module available")
        print("  Documented throughput: 18,384 msg/sec")
        print("  Documented latency: <0.05ms per message")
        print("  Architecture: Async priority queuing with pub/sub")
        print()
    except ImportError as e:
        print(f"  Status: MessageBus not available ({str(e)})")
        print("  [NOTE] Run from Grokputer root directory to access modules")
        print()


def show_pantheon_status():
    """Display Pantheon agent information."""
    print("[PANTHEON STATUS - 9 Agent System]")
    agents = [
        ("Observer", "Screen capture, vision processing, OCR"),
        ("Reasoner", "Task analysis, delegation planning"),
        ("Actor", "Command execution, computer control"),
        ("Validator", "Safety checks, risk assessment"),
        ("Learner", "Q-learning, adaptive optimization"),
        ("Memory", "Redis/SQLite persistence"),
        ("Executor", "Multi-step workflow orchestration"),
        ("Analyzer", "Performance metrics, bottleneck detection"),
        ("Improver", "Self-healing, proposal application"),
    ]

    for name, description in agents:
        print(f"  [{name:<10}] {description}")
    print()
    print("  Usage: python main.py --pantheon --task 'your task here'")
    print("  God Mode: python main.py -gp --task 'complex multi-agent task'")
    print()


def show_system_metrics():
    """Display system metrics and status."""
    print("[SYSTEM METRICS]")

    # Redis status
    redis_connected, redis_msg = check_redis_status()
    print(f"  {redis_msg}")

    # Python version
    print(f"  Python: {sys.version.split()[0]}")

    # Check for key dependencies
    dependencies = [
        ("tiktoken", "Real token counting"),
        ("redis", "Memory persistence"),
        ("anthropic", "Claude API"),
        ("openai", "OpenAI/xAI API"),
    ]

    print("\n  [DEPENDENCIES]")
    for module_name, description in dependencies:
        try:
            __import__(module_name)
            print(f"    [{module_name:<12}] INSTALLED - {description}")
        except ImportError:
            print(f"    [{module_name:<12}] MISSING   - {description}")
    print()


def show_quick_start():
    """Show quick start commands."""
    print("[QUICK START GUIDE]")
    print("  1. Basic task execution:")
    print("     python main.py --task 'your task here'")
    print()
    print("  2. Pantheon mode (9 agents):")
    print("     python main.py --pantheon --task 'complex task'")
    print()
    print("  3. Multi-provider collaboration:")
    print("     python main.py --providers grok,claude --task 'analysis task'")
    print()
    print("  4. Interactive menu:")
    print("     python main.py")
    print()
    print("  5. Run tests:")
    print("     pytest --cov")
    print()
    print("  6. Launch dashboard:")
    print("     streamlit run dashboard.py")
    print()


def interactive_demo():
    """Run interactive demo with user choices."""
    print("[INTERACTIVE DEMO]")
    print()
    print("What would you like to learn about?")
    print()
    print("  1. Token counting demonstration")
    print("  2. MessageBus performance")
    print("  3. Pantheon agent system")
    print("  4. System metrics and dependencies")
    print("  5. Quick start commands")
    print("  6. All of the above")
    print("  0. Exit")
    print()

    try:
        choice = input("Enter your choice (0-6): ").strip()
        print()

        if choice == "1":
            explain_tokens()
        elif choice == "2":
            check_messagebus_performance()
        elif choice == "3":
            show_pantheon_status()
        elif choice == "4":
            show_system_metrics()
        elif choice == "5":
            show_quick_start()
        elif choice == "6":
            explain_tokens()
            check_messagebus_performance()
            show_pantheon_status()
            show_system_metrics()
            show_quick_start()
        elif choice == "0":
            print("[EXIT] Goodbye!")
            return
        else:
            print("[ERROR] Invalid choice. Please enter a number between 0-6.")
            return

        # Ask if user wants to continue
        print()
        cont = input("Continue exploring? (y/n): ").strip().lower()
        if cont == 'y':
            interactive_demo()

    except (KeyboardInterrupt, EOFError):
        print("\n[EXIT] Goodbye!")


def show_next_steps():
    """Show what new users should do next."""
    print("[NEXT STEPS]")
    print("  1. Read README.md for project overview")
    print("  2. Review CLAUDE.md for technical reference")
    print("  3. Check docs/ folder for detailed guides")
    print("  4. Explore example workflows in examples/")
    print("  5. Join the community at https://github.com/zejzl/grokputer")
    print("  6. Start with: python main.py --help")
    print()


def main():
    """Main function to run the interactive introduction."""
    print_header()
    print_welcome()

    # Check if running in interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_demo()
    else:
        # Default non-interactive tour
        explain_tokens()
        check_messagebus_performance()
        show_pantheon_status()
        show_system_metrics()
        show_quick_start()
        show_next_steps()

        print("=" * 70)
        print("[SUCCESS] Welcome tour complete!")
        print("[TIP] Run with --interactive for interactive demo:")
        print("      python token_haze.py --interactive")
        print("=" * 70)


if __name__ == "__main__":
    main()
