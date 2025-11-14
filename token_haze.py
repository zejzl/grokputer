#!/usr/bin/env python3
"""
Token Haze - Introduction to Grokputer for New Users

This script demonstrates basic token concepts and welcomes new users to the Grokputer ecosystem.
Grokputer is an AI-powered computer control system using xAI's Grok API.

Author: Grokputer Team
Date: 2025-11-14
"""

import sys
import time

def print_welcome():
    """Print a welcoming message for new users."""
    print("🌟 Welcome to Grokputer! 🌟")
    print("You're entering the realm of autonomous AI agents.")
    print("Here, tokens are the currency of intelligence.")
    print()

def explain_tokens():
    """Explain what tokens are in the context of AI."""
    print("🔑 Understanding Tokens:")
    print("- Tokens are units of text that AI models process")
    print("- They can be words, subwords, or characters")
    print("- Grokputer uses tokens to communicate with AI models")
    print("- Efficient token usage = better performance and cost savings")
    print()

def demonstrate_token_count():
    """Simple demonstration of token counting."""
    text = "Hello, new user! Welcome to the world of AI agents."
    # Rough estimate: ~1 token per word
    token_estimate = len(text.split())
    print(f"📊 Token Demo:")
    print(f"Text: '{text}'")
    print(f"Estimated tokens: {token_estimate}")
    print("In real AI models, tokenization is more complex!")
    print()

def show_next_steps():
    """Show what new users should do next."""
    print("🚀 Next Steps for New Users:")
    print("1. Read the README.md for project overview")
    print("2. Check out main.py to run basic commands")
    print("3. Explore the docs/ folder for detailed guides")
    print("4. Consult the Visionary agent for advanced insights")
    print("5. Join the community at https://github.com/sst/opencode")
    print("6. Start with simple tasks like 'python main.py --help'")
    print()

def main():
    """Main function to run the introduction."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        content = r.get('token_haze')
        if content:
            print("Content from Redis:")
            print(content)
        else:
            print("No content in Redis, falling back to default:")
            print("=" * 60)
            print_welcome()
            explain_tokens()
            demonstrate_token_count()
            show_next_steps()
            print("Happy exploring! Remember: With great tokens comes great power. ⚡")
            print("=" * 60)
    except ImportError:
        print("Redis not available, using default:")
        print("=" * 60)
        print_welcome()
        explain_tokens()
        demonstrate_token_count()
        show_next_steps()
        print("Happy exploring! Remember: With great tokens comes great power. ⚡")
        print("=" * 60)

if __name__ == "__main__":
    main()