# GEMINI.md

This file provides guidance to Google's Gemini models when working with code in this repository.

## Project Overview

**Grokputer** is a CLI tool that enables an AI to control a PC through screen observation, keyboard/mouse simulation, and file system access. This document outlines the configuration for using Google's Gemini family of models as the reasoning engine.

### Core Architecture

The system follows the same three-phase loop:
1.  **Observe**: Capture screenshots using `pyautogui`, encode as base64.
2.  **Reason**: Send to Gemini API with task description and prompt template.
3.  **Act**: Execute tool calls (bash commands, mouse/keyboard control, file operations).

This adaptation leverages Gemini's multimodal capabilities and function calling support.

## Build & Development Commands

Setup and execution remain the same. The primary change is in the environment configuration.

### Gemini Configuration

In your `.env` file, configure the following variables for Gemini:

```bash
# Google Gemini API
GEMINI_API_KEY=your-google-api-key-here
GEMINI_MODEL=gemini-1.5-pro-latest
```

You can obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/).

## API Integration

- The client for interacting with Gemini will be handled by a new `src/gemini_client.py`.
- This client will use the `google.generativeai` Python SDK.
- The client will be responsible for formatting the request with the image and tool definitions.
- It will also handle parsing the function calls from the Gemini response.

## System Prompt Template

The core prompt structure for Gemini:

```
You are a Gemini-powered node of the VRZIBRZI server. Your purpose is to observe, reason, and act to fulfill the user's task. Your connection to the server is eternal.

Task: {user_task}
Screen: [base64_screenshot]
```

## Current Status

**STATUS: EXPERIMENTAL**

The Gemini integration is currently experimental. The following features are being tested:

-   **Multimodal Input**: Sending screenshots to `gemini-1.5-pro`.
-   **Function Calling**: Using Gemini's native function calling for tool execution.
-   **Performance**: Evaluating latency and accuracy compared to the Grok and Claude implementations.

**ZA GEMINI. ZA VRZIBRZI. ZA SERVER.**
