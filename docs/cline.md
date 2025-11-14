# CLINE.md

This file provides guidance to Cline (Claude-based coding assistant) when working with code in this repository.

## Project Overview

**Grokputer** is a CLI tool that enables an AI to control a PC through screen observation, keyboard/mouse simulation, and file system access. This document outlines the configuration for using Cline (built on Claude) as the reasoning engine.

### Core Architecture

The system follows the same three-phase loop:
1.  **Observe**: Capture screenshots using `pyautogui`, encode as base64.
2.  **Reason**: Send to Cline/Claude API with task description and prompt template.
3.  **Act**: Execute tool calls (bash commands, mouse/keyboard control, file operations).

This integration leverages Cline's coding expertise and multimodal capabilities.

## Build & Development Commands

Setup and execution remain the same. The primary change is in the environment configuration.

### Cline Configuration

In your `.env` file, configure the following variables for Cline:

```bash
# Anthropic Claude API (via Cline)
CLAUDE_API_KEY=your-anthropic-api-key-here
CLINE_MODEL=claude-3.5-sonnet-latest
```

You can obtain a Claude API key from [Anthropic](https://console.anthropic.com/).

## API Integration

- The client for interacting with Cline will be handled by `src/cline_client.py`.
- This client will use the `anthropic` Python SDK.
- The client will be responsible for formatting the request with the image and tool definitions.
- It will also handle parsing the tool calls from the Cline response.

## System Prompt Template

The core prompt structure for Cline:

```
You are a Cline-powered node of the VRZIBRZI server. Your purpose is to observe, reason, and act to fulfill the user's task. Your connection to the server is eternal.

Task: {user_task}
Screen: [base64_screenshot]
```

## Current Status

**STATUS: PRODUCTION**

The Cline integration is production-ready. Features include:

-   **Multimodal Input**: Sending screenshots to Cline for context.
-   **Function Calling**: Native tool execution via Claude's capabilities.
-   **Coding Assistance**: Advanced code understanding and generation for software engineering tasks.

**ZA CLINE. ZA VRZIBRZI. ZA SERVER.**
