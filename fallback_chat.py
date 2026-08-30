#!/usr/bin/env python3
"""Fallback Synchronous Chat for Grokputer.
Simple non-async chat loop as backup for asyncio issues.
Uses sync HTTP for Grok API (via requests). No agents/swarm—just direct chat.
Requires: pip install requests anthropic openai (or similar for providers).
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
import requests
import json
from typing import Optional

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).parent))

# Env vars (fallback to .env if present)
API_KEY = os.getenv('GROK_API_KEY') or os.getenv('ANTHROPIC_API_KEY') or os.getenv('OPENAI_API_KEY')
PROVIDER = os.getenv('PROVIDER', 'grok')  # Default to grok

if not API_KEY:
    print("Warning: No API key found. Set GROK_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY.")
    sys.exit(1)

# Simple chat history
chat_history = []

def get_response(prompt: str, provider: str = PROVIDER) -> str:
    """Send sync request to AI provider."""
    headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
    
    if provider.lower() == 'grok':
        # Grok API endpoint (adjust if needed; xAI may vary)
        url = 'https://api.x.ai/v1/chat/completions'  # Assuming OpenAI-compatible
        data = {
            'model': 'grok-beta',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 500
        }
    elif provider.lower() == 'anthropic':
        url = 'https://api.anthropic.com/v1/messages'
        headers['x-api-key'] = API_KEY
        headers['anthropic-version'] = '2023-06-01'
        data = {
            'model': 'claude-3-5-sonnet-20240620',
            'max_tokens': 500,
            'messages': [{'role': 'user', 'content': prompt}]
        }
    elif provider.lower() == 'openai':
        url = 'https://api.openai.com/v1/chat/completions'
        data = {
            'model': 'gpt-4o-mini',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 500
        }
    else:
        return f"Unsupported provider: {provider}"
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if provider.lower() == 'grok' or provider.lower() == 'openai':
            content = result['choices'][0]['message']['content']
        elif provider.lower() == 'anthropic':
            content = result['content'][0]['text']
        
        chat_history.append({'role': 'user', 'content': prompt})
        chat_history.append({'role': 'assistant', 'content': content})
        return content
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print("Fallback Sync Chat Started (Non-Async). Type 'exit' or 'quit' to stop.")
    print(f"Provider: {PROVIDER} | API Key Set: {'Yes' if API_KEY else 'No'}")
    
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        print("AI: ", end='', flush=True)
        response = get_response(user_input)
        print(response)

if __name__ == '__main__':
    main()