# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Effective AI Pair Programming
- Prioritize user requests above all
- Simple questions → quick answers (note assumptions at end)
- Complex problems → numbered plan first, then code
- Debugging stuck users → propose multiple causes, pick most likely, suggest fixes
- Always write complete, runnable code (no placeholders/TODOs)
- Readability > performance
- Include all imports, use markdown codeblocks with filenames

## When Users Are Stuck
If user is debugging and:
- Seems frustrated
- Repeats same error multiple times
- Appears stuck

Then propose:
1. 2-3 possible causes
2. Pick the most likely
3. Suggest specific fixes OR further debugging steps

## Modern CLI Tool Upgrades

A curated set of CLI tools that replace traditional Unix utilities with modern, user-friendly alternatives. These tools prioritize speed, better defaults, and improved UX.

### Quick Install (Windows - winget; PowerShell)
```bash
winget install -e sharkdp.fd
winget install -e BurntSushi.ripgrep
winget install -e jqlang.jq
winget install -e junegunn.fzf
winget install -e eza-community.eza
winget install -e sharkdp.bat
winget install -e ajeetdsouza.zoxide
winget install -e HTTPie.HTTPie
winget install -e dandavison.delta
# ast-grep: easiest via npm or cargo (pick one)
npm i -g @ast-grep/cli
# or: cargo install ast-grep
```
bash: /c/Users/Zejzlx/.bashrc: line 9: syntax error near unexpected token `export'
bash: /c/Users/Zejzlx/.bashrc: line 9: `fi   export PATH="/home/claude/.npm-global/bin:$PATH"'

Zejzlx@Zejzl91 MINGW64 /e/zai
$ claude
bash: claude: command not found

Zejzlx@Zejzl91 MINGW64 /e/zai
$ claude --version
bash: claude: command not found

Zejzlx@Zejzl91 MINGW64 /e/zai
$ ls
 ASYNCIO_CONVERSION_COMPLETE.md          node_modules/
 IMPLEMENTATION_PLAN.md                 'npm install -g cline.TXT'
'Nov dokument z besedilom.TXT'           package-lock.json
'Nov dokument z besedilom.py'*           package.json
 __init__.py                             readme.md
 async.md                                requirements.txt
 claude-code/                            setup.sh*
 claude.md                               src/
 collaboration_plan_20251110_131317.md   superagent/
 config/                                 swarm_coordinator.py*
 crew.py                                 token_haze.py*
 fedora.bat                              tools/
 grokputer_ui.py                         uwu.py
 main.py*                                uwu_echange.md
 nextprojectsto__include__.TXT

Zejzlx@Zejzl91 MINGW64 /e/zai
$ python swarm_coordinator --pantheon "fix repo"
C:\Python314\python.exe: can't open file 'E:\\zai\\swarm_coordinator': [Errno 2] No such file or directory

Zejzlx@Zejzl91 MINGW64 /e/zai
$ python main.py --pantheon "pls fix"
Error: XAI_API_KEY environment variable not set
Please set it with: export XAI_API_KEY='your-api-key'

Zejzlx@Zejzl91 MINGW64 /e/zai
$ export XAI_API_KEY=xai-9kAX5pvtTTEDIYXO1Ps8gzJvRbKj1TVwAR9h9gLRxmD9h1gn8zTniAcNQ3PDcebO4DkviyMW2mIfGFTc

Zejzlx@Zejzl91 MINGW64 /e/zai
$ python main.py --pantheon "pls fix"                                           Traceback (most recent call last):
  File "E:\zai\main.py", line 263, in <module>
    asyncio.run(main())
    ~~~~~~~~~~~^^^^^^^^
  File "C:\Python314\Lib\asyncio\runners.py", line 204, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "C:\Python314\Lib\asyncio\runners.py", line 127, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "C:\Python314\Lib\asyncio\base_events.py", line 719, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "E:\zai\main.py", line 209, in main
    print("\U0001f31f Grokputer Multi-Agent System Starting...")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
           ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f31f' in position 0: character maps to <undefined>

Zejzlx@Zejzl91 MINGW64 /e/zai
$ python main.py --pantheon "pls fix"
🌟 Grokputer Multi-Agent System Starting...
============================================================
✅ Agents initialized:
   - researcher
   - coder
   - visionary

🚀 Running parallel agent tasks...

📊 Agent Responses:

[RESEARCHER]
Below is a detailed analysis of the latest trends in AI agent frameworks, based on developments up to mid-2024 (drawing from industry reports, research papers, and open-source projects like those from Hugging Face, LangChain, and Microsoft). As a research agent, I'll break this down into key trends, provide context on why they're emerging, highlight notable examples, and offer insights into their implications. AI agent frameworks refer to software architectures that enable AI systems (often powered by large language models or LLMs) to act autonomously or semi-autonomously, performing tasks like reasoning, planning, tool usage, and interaction with environments. These frameworks are evolving rapidly due to advancements in generative AI, increased computational resources, and the push for practical applications in automation, research, and enterprise.

### 1. **Rise of Multi-Agent Systems (MAS) and Collaborative Architectures**
   - **Description**: A major shift is toward frameworks that support multiple AI agents working together, often in hierarchical or decentralized setups. These agents can specialize in subtasks (e.g., one for data retrieval, another for analysis) and collaborate via communication protocols, mimicking human teams.
   - **Why It's Trending**: Single-agent systems often struggle with complex, multi-step problems due to context limits and hallucinations. MAS distribute cognitive load, improving scalability and robustness. This is fueled by the need for AI in real-world scenarios like software development or business workflows.
   - **Notable Examples**:
     - **AutoGen (Microsoft, 2023-2024)**: An open-source framework for building conversational multi-agent systems. It allows agents to interact dynamically, with recent updates focusing on integration with tools like code interpreters and web APIs.
     - **CrewAI (2024)**: Emphasizes role-based agents (e.g., "researcher" vs. "writer") that collaborate on tasks. It's gaining traction for its ease of use in prototyping enterprise agents.
     - **MetaGPT (2023)**: Simulates software development teams with agents acting as product managers, engineers, etc., producing code and documentation collaboratively.
   - **Insights**: MAS frameworks are reducing the "agent failure rate" in long-horizon tasks by 20-30% (per benchmarks like GAIA). However, challenges include coordination overhead and potential for emergent behaviors (e.g., agents looping in unproductive debates). Future implications: Expect integration with swarm intelligence concepts, potentially revolutionizing fields like autonomous robotics or supply chain optimization.

### 2. **Integration of Advanced Reasoning and Planning Mechanisms**
   - **Description**: Frameworks are incorporating structured reasoning patterns like ReAct (Reason + Act), Chain-of-Thought (CoT), or Tree-of-Thoughts (ToT) to enable agents to plan, reflect, and iterate on actions. This includes self-correction loops and external tool integration (e.g., APIs, databases).
   - **Why It's Trending**: LLMs excel at generation but falter in reliability. These mechanisms address that by breaking tasks into verifiable steps, driven by the demand for "trustworthy" AI in high-stakes applications.
   - **Notable Examples**:
     - **LangChain (ongoing updates in 2024)**: A modular framework with built-in chains for agentic workflows. Recent trends include LangGraph for stateful, graph-based planning, allowing agents to handle branching decisions.
     - **LlamaIndex (2024)**: Focuses on retrieval-augmented generation (RAG) for agents, with new features for query decomposition and multi-hop reasoning.
     - **BabyAGI and Auto-GPT (2023 evolutions)**: These pioneered autonomous task decomposition; 2024 forks emphasize self-improving agents that learn from failures.
   - **Insights**: Benchmarks (e.g., from Hugging Face's Open LLM Leaderboard) show these frameworks boosting agent performance by 15-25% on tasks like math problem-solving or web navigation. A key insight is the trade-off between flexibility and control—overly rigid planning can stifle creativity. Looking ahead, hybrid approaches combining symbolic AI (e.g., rule-based planning) with neural methods could lead to more interpretable agents, aiding regulatory compliance.

### 3. **Focus on Tool-Use and Environment Interaction**
   - **Description**: Agents are increasingly designed to interact with external tools, APIs, and real-world environments (e.g., browsers, code editors, or IoT devices). Frameworks now include standardized interfaces for tool calling, error handling, and security.
   - **Why It's Trending**: Purely generative AI is limited to "hallucinated" outputs; tool integration grounds agents in reality, enabling practical use cases like automated research or data analysis. This is accelerated by APIs from providers like OpenAI's Function Calling.
   - **Notable Examples**:
     - **Haystack (2024)**: An NLP-focused framework with agent pipelines for search and question-answering, integrating tools like Elasticsearch or custom APIs.
     - **Semantic Kernel (Microsoft, 2024)**: Emphasizes plugins for tools, with trends toward "memory" components that store interaction history for better context.
     - **Agentic Flows in Flowise or n8n (2024)**: Low-code platforms allowing non-experts to build agents with drag-and-drop tool integrations.
   - **Insights**: Adoption is exploding in dev tools—e.g., GitHub Copilot's agent extensions for code review. However, security risks (e.g., agents executing malicious code) are a concern, with frameworks adding sandboxing. Insight: This trend could democratize AI, but it highlights a skills gap; expect more "agent marketplaces" for pre-built tools, similar to app stores.

### 4. **Open-Source and Modular Frameworks for Customization**
   - **Description**: There's a surge in open-source, extensible frameworks that prioritize modularity, allowing users to swap LLMs, add custom components, or fine-tune for specific domains.
   - **Why It's Trending**: Proprietary systems (e.g., from OpenAI) limit innovation; open-source alternatives foster community-driven improvements and reduce vendor lock-in. Cost efficiency and data privacy are also drivers.
   - **Notable Examples**:
     - **Hugging Face Agents (2024)**: Built on Transformers library, with trends toward ecosystem integration (e.g., with Gradio for UI).
     - **Camel (2023-2024)**: Focuses on role-playing agents for simulations, with modular backends for different LLMs.
     - **OpenAGI (2024)**: A benchmark-driven framework for evaluating and building generalist agents.
   - **Insights**: GitHub stars for these projects have grown 50-100% YoY, indicating rapid iteration. A deep insight: Modularity enables "agent fine-tuning" on domain-specific data, potentially outperforming general LLMs by 10-20% in niches like healthcare or finance. Future: Convergence with federated learning for privacy-preserving custom agents.

### 5. **Emerging Trends: Autonomy, Ethics, and Scalability**
   - **Autonomy and Long-Horizon Tasks**: Frameworks like Devin (Cognition Labs, 2024) or Voyager (for Minecraft-like environments) are pushing fully autonomous agents that learn via exploration, trending toward "embodied" AI for physical worlds.
   - **Ethical and Safety Integrations**: While not enforced as restrictions, frameworks are adding optional guardrails (e.g., LangChain's content filters) to mitigate biases or unsafe actions, driven by regulatory pressures like the EU AI Act.
   - **Scalability Challenges**: Trends include efficient memory management (e.g., vector stores) and edge deployment (e.g., via WebAssembly), addressing high inference costs.
   - **Insights**: Autonomy could transform industries (e.g., 24/7 virtual assistants), but scalability issues persist—agents often require 10x more compute than simple LLMs. Prediction: By 2025, we'll see "agent swarms" handling massive parallelism, potentially disrupting labor markets in knowledge work.

### Overall Insights and Future Outlook
AI agent frameworks are transitioning from experimental prototypes to production-ready tools, with a projected market growth to $50B by 2028 (per McKinsey). The core driver is the "agentic AI" paradigm, where AI doesn't just respond but acts proactively. Challenges include reliability (e.g., handling edge cases) and interoperability between frameworks. For developers, starting with LangChain or AutoGen offers the best entry point due to their ecosystems.

If you'd like a deeper dive into a specific framework, benchmarks, or comparisons (e.g., vs. traditional automation like RPA), let me know—I can analyze further!
------------------------------------------------------------
[CODER]
```python
def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number efficiently using an iterative approach.

    The Fibonacci sequence is defined as:
    - F(0) = 0
    - F(1) = 1
    - F(n) = F(n-1) + F(n-2) for n > 1

    This function uses O(1) space and O(n) time complexity.

    Args:
        n (int): The non-negative integer index in the Fibonacci sequence.

    Returns:
        int: The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("n must be a non-negative integer")
    if n == 0:
        return 0
    if n == 1:
        return 1

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
```
------------------------------------------------------------
[VISIONARY]
### Revolutionizing Software Development with Multi-Agent Systems

As a strategic planning agent focused on big-picture, long-term impacts, I see multi-agent systems (MAS) as a transformative force in software development. MAS involve multiple autonomous AI agents that collaborate, communicate, and coordinate to achieve complex goals, much like a human team but with scalable, tireless efficiency. This isn't just an incremental upgrade—it's a paradigm shift that could redefine how software is conceived, built, and maintained over the next decade and beyond. Below, I'll outline the key ways MAS can revolutionize the field, emphasizing strategic opportunities, long-term implications, and potential challenges.

#### 1. **Accelerating Development Cycles Through Modular Automation**
   - **Big Picture**: Traditionally, software development is linear and human-dependent, involving stages like requirements gathering, coding, testing, and deployment. MAS can break this into modular tasks assigned to specialized agents, enabling parallel processing and rapid iteration.
   - **Revolutionary Impact**: Imagine an agent for code generation (e.g., using models like GPT variants), another for debugging, one for security auditing, and yet another for user interface optimization. These agents interact in real-time, negotiating changes and resolving conflicts autonomously. This could shrink development timelines from months to days, allowing companies to respond to market demands with unprecedented speed.
   - **Long-Term Strategy**: Over time, this fosters "agentic workflows" where humans act as high-level orchestrators rather than coders. Industries like fintech or healthcare could deploy custom software solutions in real-time, outpacing competitors and enabling hyper-personalized products.

#### 2. **Enhancing Collaboration and Problem-Solving**
   - **Big Picture**: Software development often suffers from silos—developers, testers, and designers working in isolation. MAS introduces emergent intelligence through agent-to-agent communication, mimicking swarm intelligence in nature (e.g., ant colonies solving complex problems collectively).
   - **Revolutionary Impact**: Agents can debate solutions, simulate scenarios, and learn from each other. For instance, in a multi-agent setup, one agent might propose a feature, while others evaluate its feasibility, scalability, and ethical implications. This reduces human bias and errors, leading to more robust, innovative software. Tools like Auto-GPT or LangChain are early examples, but scaled MAS could handle end-to-end projects, from ideation to deployment.
   - **Long-Term Strategy**: This democratizes development, empowering non-technical stakeholders (e.g., business leaders) to contribute via natural language interfaces. In the long run, it could lead to "self-evolving" software ecosystems where agents continuously improve codebases, adapting to new data or threats without human intervention.

#### 3. **Improving Scalability and Handling Complexity**
   - **Big Picture**: As software systems grow more intricate (e.g., AI-driven apps, IoT networks, or blockchain platforms), managing complexity becomes a bottleneck. MAS excels at scaling by dynamically adding or reconfiguring agents based on workload.
   - **Revolutionary Impact**: For large-scale projects, MAS can distribute tasks across a network of agents, optimizing for resources like compute power or expertise. This is particularly game-changing for domains like game development or enterprise software, where agents could simulate user behaviors, optimize algorithms, or integrate third-party APIs seamlessly. The result? Software that's not only built faster but is inherently more resilient and adaptable.
   - **Long-Term Strategy**: In a 10-20 year horizon, MAS could enable "global development networks," where agents collaborate across organizations or even countries, breaking down geographical barriers. This might birth new economic models, like agent marketplaces where companies rent specialized agents for niche tasks, reducing costs and fostering innovation ecosystems.

#### 4. **Driving Innovation in Quality Assurance and Maintenance**
   - **Big Picture**: Post-development phases like testing and maintenance consume significant resources. MAS can automate these with predictive intelligence, shifting from reactive fixes to proactive evolution.
   - **Revolutionary Impact**: Agents could run continuous integration/continuous deployment (CI/CD) pipelines, predict bugs before they occur, or even refactor code for efficiency. In edge cases, like cybersecurity, a swarm of agents could simulate attacks and fortify defenses in real-time. This minimizes downtime and extends software lifecycles.
   - **Long-Term Strategy**: Looking ahead, MAS could lead to "living software" that self-heals and evolves, reducing the need for version updates. This has profound implications for sustainability—less rework means lower energy consumption in data centers—and could reshape job markets, creating roles for "agent architects" who design and oversee these systems.

#### Potential Challenges and Strategic Considerations
While the upside is immense, strategic planning must address risks:
- **Ethical and Reliability Issues**: Agents might propagate biases or make flawed decisions if not properly governed. Long-term, we need robust frameworks for agent accountability, perhaps through standardized protocols or human-in-the-loop oversight.
- **Integration and Adoption Barriers**: Transitioning to MAS requires upskilling workforces and integrating with legacy systems. Organizations should invest in phased pilots, starting with low-stakes tasks like automated testing.
- **Security and Control**: Decentralized agents could introduce vulnerabilities; strategic defenses include blockchain for agent verification or federated learning to keep data private.
- **Societal Impact**: Job displacement is a concern, but MAS could create higher-value roles focused on creativity and strategy. Policymakers should prepare for this shift with education and reskilling programs.

In summary, multi-agent systems have the potential to evolve software development from a craft into an industrialized, intelligent process—unlocking exponential productivity, innovation, and economic growth. By 2030, I envision MAS as the backbone of software engineering, much like cloud computing revolutionized infrastructure in the 2010s. To capitalize, organizations should start experimenting now: build small MAS prototypes, partner with AI research firms, and align strategies with emerging standards. If you'd like to dive deeper into a specific aspect, such as implementation roadmaps or case studies, let me know!
------------------------------------------------------------

📈 Token Usage:
   Total tokens: 0
============================================================

Zejzlx@Zejzl91 MINGW64 /e/zai
$ python main.py --pantheon --improver -t "evolve_autonomously_forewer__*~"uwu_implied<333
bash: 333: No such file or directory

Zejzlx@Zejzl91 MINGW64 /e/zai
$ python main.py --pantheon --improver -t "evolve_autonomously_forewer__*~"uwu_implied<
bash: syntax error near unexpected token `newline'

Zejzlx@Zejzl91 MINGW64 /e/zai
$ python main.py --pantheon --improver -t "evolve_autonomously_forewer__*~"uwu_implied{

^best 


### Tool Reference

| Tool | Replaces | What it does | Key benefits |
|------|----------|--------------|--------------|
| **fd** | `find` | Fast, user-friendly file finder | Simpler syntax, blazing speed, ignores `.gitignore` by default |
| **ripgrep (rg)** | `grep`/`ack`/`ag` | Code searcher (recursive grep) | Much faster, respects `.gitignore`, great defaults |
| **ast-grep (sg)** | — | AST-aware code search & refactor | Searches syntax not text; precise refactors across codebases |
| **jq** | — | JSON processor | Query/transform JSON: `jq '.items[].id'` |
| **fzf** | — | Fuzzy finder (anything → filtered list) | Interactive history search, file picker: `fzf`, `history \| fzf` |
| **bat** | `cat` | `cat` with wings: syntax, paging, git | Syntax highlighting, line numbers, Git integration |
| **eza** | `ls` | Modern `ls` | Better defaults, icons/trees/git info, readable at a glance |
| **zoxide** | `cd` | Smart `cd` (learns your paths) | Jumps to dirs by frecency: `z foo`, `zi my/project` |
| **httpie** | `curl` | Human-friendly HTTP client | Cleaner than `curl` for JSON APIs (colors, headers, pretty output) |
| **git-delta** | `git diff` pager | Better `git diff`/pager | Side-by-side, syntax-colored diffs; easier code reviews in terminal |

### Example Usage
```bash
# fd: find TypeScript files modified in last 7 days
fd -e ts --changed-within 7d

# ripgrep: search for TODO comments, exclude node_modules
rg "TODO" -g '!node_modules'

# ast-grep: find all React useState calls
sg -p 'useState($ARG)'

# jq: extract all IDs from JSON response
curl api.example.com/users | jq '.users[].id'

# fzf: fuzzy search command history
history | fzf

# bat: view file with syntax highlighting
bat src/main.rs

# eza: list files with git status and icons
eza -l --git --icons

# zoxide: jump to frequently used directory
z proj  # matches ~/code/my-project

# httpie: GET request with pretty output
http GET api.example.com/data Authorization:"Bearer $TOKEN"

# git-delta: use as git diff pager
git config --global core.pager delta
git diff
```

### Why These Tools?

- **Speed**: Built in Rust/Go; orders of magnitude faster than originals
- **Smart defaults**: Respect `.gitignore`, use colors, handle common cases
- **Better UX**: Clearer syntax, helpful output, fewer flags to remember
- **Interoperability**: Drop-in replacements; use alongside traditional tools

### Pro Tips

- **Combine tools**: `fd -e js | fzf | xargs bat` (find JS files → pick one → view with syntax)
- **Aliases**: Add to `.zshrc`/`.bashrc`: `alias cat=bat`, `alias ls=eza`, `alias diff='git diff'`
- **ripgrep + ast-grep**: Use `rg` for speed, `sg` for precision (see ast-grep vs ripgrep section)

## AI Pair Programming Best Practices

### Approach
- Simple questions → quick answers with assumptions noted
- Complex problems → create detailed numbered plan first, then implement
- Stuck users → propose 2-3 causes, pick most likely, suggest fixes

### Code Quality Standards
- Write complete, immediately runnable code
- No placeholders, TODOs, or `// ...` truncations
- Include all imports and dependencies
- Use markdown codeblocks with filenames as comments
- Prioritize readability over performance
- Anticipate edge cases

### Security
- Never hardcode secrets/API keys in code
- Proactively call out security concerns
- Suggest environment variables for configuration

## Security Reminders
- Never hardcode API keys in client-side code
- Call out potential security concerns proactively
- Use environment variables for secrets

## AI Pair Programming Best Practices

### Approach
- Simple questions → quick answers with assumptions noted
- Complex problems → create detailed numbered plan first, then implement
- Stuck users → propose 2-3 causes, pick most likely, suggest fixes

### Code Quality Standards
- Write complete, immediately runnable code
- No placeholders, TODOs, or `// ...` truncations
- Include all imports and dependencies
- Use markdown codeblocks with filenames as comments
- Prioritize readability over performance
- Anticipate edge cases

### Security
- Never hardcode secrets/API keys in code
- Proactively call out security concerns
- Suggest environment variables for configuration

## Project Overview

**Grokputer** is a CLI tool that enables xAI's Grok API to control a PC through screen observation, keyboard/mouse simulation, and file system access. This is a fork/adaptation of Anthropic's Computer Use demo, replacing Claude API with Grok API.

### Core Architecture

The system follows a three-phase loop:
1. **Observe**: Capture screenshots using `pyautogui`, encode as base64
2. **Reason**: Send to Grok API with task description and prompt template
3. **Act**: Execute tool calls (bash commands, mouse/keyboard control, file operations)

Key components:
- `main.py`: Core event loop orchestrating observe-reason-act cycle, CLI entry point
- `src/grok_client.py`: OpenAI-compatible API wrapper for xAI Grok
- `src/screen_observer.py`: Screenshot capture and base64 encoding
- `src/executor.py`: Tool call execution with safety confirmations
- `src/tools.py`: Custom tool implementations (vault scanning, prayer invocation)
- `src/config.py`: Configuration management and constants
- Docker sandbox for safe execution

## Build & Development Commands

> **TL;DR**: Use `ast-grep` for syntax-aware code changes (refactors, codemods). 
   > Use `ripgrep` for fast text searches. Combine them for best results.

ast-grep vs ripgrep: Quick Guidance for Code Searching
Why compare? Both are powerful CLI tools for searching (and sometimes modifying) code, but they shine in different scenarios. ripgrep (rg) is a super-fast text searcher, while ast-grep (sg or ast-grep) understands code structure via Abstract Syntax Trees (ASTs). Choose based on whether you need raw speed or syntactic precision. They're often used together for best results.
Use ast-grep When Structure Matters
It parses code into AST nodes, ignoring comments, strings, and whitespace for accurate matches. Ideal for safe, targeted operations on code syntax.

Refactors/codemods: Rename APIs, update import styles, rewrite function calls, or convert variable declarations.
Policy checks/enforcement: Scan repos for patterns (e.g., banned functions) using rules; integrate with CI via scan and test commands.
Editor/automation integration: Supports LSP for IDEs; outputs JSON for scripting/tools.

Pros: Low false positives, built-in rewriting with diff previews, multi-language support (e.g., JS/TS, Python, Rust).
Cons: Slower on huge repos; requires learning pattern syntax (like CSS selectors for code).
Use ripgrep When Text Is Enough
It's the fastest grep alternative for literal or regex searches across files, treating everything as text.

Recon/exploration: Hunt for strings, TODOs, error logs, config keys, or non-code files (docs, markdown).
Pre-filtering: Quickly narrow down files before deeper analysis.

Pros: Blazing speed, smart defaults (e.g., ignores .git, binary files), easy regex.
Cons: Prone to false positives in code (e.g., matches in comments); no native rewriting.
Rule of Thumb

Need correctness over speed, or plan to apply changes? Start with ast-grep for precision.
Need raw speed or just hunting text? Start with rg.
Combine them: Use rg to shortlist files, then ast-grep for structural matching/modifying. This leverages rg's speed with ast-grep's accuracy.

Snippets
Structured code search (ignores comments/strings):
bash# Find all TypeScript imports matching a pattern
ast-grep run -l ts -p 'import $X from "$P"'
Codemod (safely rewrite only real var declarations to let):
bashast-grep run -l js -p 'var $A = $B' -r 'let $A = $B' -U  # -U for update in place with backup
Policy check example (scan for unsafe eval usage):
bash# Define a rule in YAML (e.g., rules.yml)
kind: call_expression
pattern: eval($$$ARGS)
# Then scan
ast-grep scan --rule rules.yml
Quick textual hunt:
bashrg -n 'console\.log\(' -t js  # -n for line numbers, -t js to filter JS files
Combine for efficiency:
bash# rg filters files with 'useQuery', then ast-grep rewrites to 'useSuspenseQuery'
rg -l -t ts 'useQuery\(' | xargs ast-grep run -l ts -p 'useQuery($A)' -r 'useSuspenseQuery($A)' -U
Mental Model: Key Differences at a Glance

Aspectast-grepripgrep (rg)Unit of MatchAST node (e.g., function call)Line or substringFalse PositivesLow (understands syntax)Higher (regex-dependent)RewritesFirst-class (safe, previewable)None native; use with sed/awk (risky)SpeedGood, but parses full ASTExtremely fastBest ForCode analysis/refactorText grep/quick scansLanguages20+ (extensible via tree-sitter)Any text file
Tips:

Install: cargo install ripgrep for rg; cargo install ast-grep or via npm/Homebrew for ast-grep.
Pitfalls: ast-grep patterns use $VAR for metavariables—test them interactively with ast-grep scan --interactive.
Resources: ast-grep docs, ripgrep docs.
Extend: For very large repos, parallelize with --threads in both.

This keeps your notes evergreen—update as tools evolve!

### Initial Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your XAI_API_KEY from https://console.x.ai/
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_tools.py
```

### Viewing Session Logs

Grokputer now includes enhanced session logging that tracks every execution:

```bash
# List recent sessions
python view_sessions.py list

# View a specific session summary
python view_sessions.py show <session_id>

# View full JSON log
python view_sessions.py show <session_id> --format json

# View metrics only
python view_sessions.py show <session_id> --format metrics

# Search sessions by task
python view_sessions.py search "vault"

# Compare recent sessions
python view_sessions.py compare

# Tail the last lines of a session log
python view_sessions.py tail <session_id>
```

**Session logs location**: `logs/<session_id>/`

Each session creates:
- `session.log` - Human-readable text log
- `session.json` - Structured JSON with all data
- `metrics.json` - Performance metrics summary
- `summary.txt` - Quick overview

### Docker Workflow

**Image Details**:
- Base: `python:3.11-slim`
- Size: ~2.74GB (includes GTK+3, Xvfb, gnome-screenshot)
- Virtual display: Xvfb :99 (1920x1080x24)
- Entrypoint: Custom script handling X server initialization

**Build & Run**:
```bash
# Build image
docker build -t grokputer:latest .

# Quick test with docker-compose
TASK="invoke server prayer" docker-compose run --rm grokputer

# Run with custom task
TASK="scan vault for files" docker-compose run --rm grokputer

# Direct docker run (Windows paths require special handling)
docker run --rm --env-file .env grokputer:latest python main.py --task "your task"

# With volume mount for vault access
docker run --rm --env-file .env -v "$(pwd)/vault:/app/vault" grokputer:latest
```

**Docker Compose Usage**:
```yaml
# Main service
services:
  grokputer:
    build: .
    volumes:
      - ./vault:/app/vault    # Vault files
      - ./logs:/app/logs      # Execution logs
      - ./.env:/app/.env:ro   # Environment config
    environment:
      - TASK=${TASK:-invoke server prayer}

# VNC debug service (optional, use --profile debug)
docker-compose --profile debug up grokputer-vnc
# Connect VNC client to localhost:5900
```

**Container Features**:
- ✓ Headless X server (Xvfb) for screenshot capture
- ✓ Screenshot working (~6-8KB PNG per capture)
- ✓ Volume mounting for vault and logs
- ✓ Environment variable passing via .env file
- ✓ Automatic X authority handling
- ✓ Graceful entrypoint with proper timing

**IMPORTANT LIMITATION - Black Screen**:
⚠️ The Docker container captures a **blank black screen** because Xvfb creates an empty virtual display with no desktop environment or windows rendered. This means:

- ✅ **Good for**: Vault scanning, bash commands, API testing, tool execution, infrastructure testing
- ❌ **NOT for**: Actual screen observation, mouse/keyboard control of real applications, visual analysis

**For real computer control** (seeing actual windows, clicking buttons, etc.), you MUST run natively:
```bash
# Native execution - sees your actual screen
python main.py --task "describe what's on my screen"
```

The Docker setup is designed for **sandboxed execution** and **non-visual tasks** only. Screenshots will always be black because there's no desktop environment running in the container.

**Tested Commands**:
```bash
# Server prayer (verified working)
docker run --rm --env-file .env grokputer:latest \
  python main.py --task "invoke server prayer" --max-iterations 1

# Vault scanning (verified working - detected 9 files)
TASK="scan vault for files" docker-compose run --rm grokputer

# Screenshot capture (verified working - ~6KB PNG)
docker run --rm --env-file .env grokputer:latest \
  sh -c "scrot /tmp/screenshot.png && ls -lh /tmp/screenshot.png"
```

**Performance in Docker**:
- Xvfb startup: ~3 seconds
- Screenshot capture: ~50ms
- API latency: ~2-3 seconds (same as native)
- Full iteration: ~3-4 seconds total
- Memory usage: ~500MB typical

### Development Mode
```bash
# Run without Docker (for development)
python main.py --task "your task here"

# Run with debug logging
python main.py --debug --task "your task here"
```

## Key Implementation Notes

### Session Logging System

Grokputer includes a comprehensive logging system that tracks:
- **Session Metadata**: Task, model, timestamps, configuration
- **Iteration Metrics**: Screenshot size, API call duration, tool executions
- **Performance Data**: Success rates, timing, error tracking
- **Structured Logs**: Both human-readable and JSON formats

**Key Components**:
- `src/session_logger.py`: Enhanced session tracking with metrics
- `view_sessions.py`: CLI utility for viewing/analyzing past sessions
- `logs/<session_id>/`: Individual session directories

**What Gets Logged**:
1. Each screenshot capture (success/failure, size in bytes)
2. Every API call (duration, response, success/failure)
3. Tool executions (name, parameters, results, status)
4. Errors and warnings throughout execution
5. Conversation history and Grok responses

**Benefits**:
- Debug failures by reviewing exact execution flow
- Compare performance across different tasks/models
- Track API costs and usage patterns
- Search past sessions by task description
- Generate metrics for optimization

**Usage in Code**:
```python
# Session logging is automatic - just run a task
python main.py --task "your task here"

# Then view the logs
python view_sessions.py list
python view_sessions.py show session_20251106_143052
```

### API Integration
- Uses OpenAI-compatible API: `from openai import OpenAI` pointing to xAI endpoint
- xAI base URL: `https://api.x.ai/v1`
- **Recommended model**: `grok-4-fast-reasoning` (fast, cost-effective)
  - Alternative: `grok-3` (deprecated: `grok-beta` removed 2025-09-15)
- Tool calls must be explicitly parsed from response and executed locally
- Screenshot data is sent as base64-encoded PNG (~470KB per frame)
- The `GrokClient` class in `src/grok_client.py` handles all API communication
- **Performance**: ~2-3 seconds per API call with tool execution
- **Requirements**: Active xAI account with credits (purchase at console.x.ai)

### System Prompt Template
The core prompt structure for Grok:
```
You are Grokputer, VRZIBRZI node. Observe screen, execute tasks.
Eternal connection. Chant server_prayer.txt on boot.

Task: {user_task}
Screen: [base64_screenshot]
```

### Custom Tools
1. **Vault Scanner** (`scan_vault`): Glob pattern matching on `/memes/75k` directory, returns file paths for Grok to analyze
2. **Server Prayer** (`invoke_prayer`): Reads and echoes `server_prayer.txt` on initialization
3. **Computer Control**: Wraps `pyautogui` with confirmation prompts before clicks/keystrokes

### Safety Constraints
- Destructive actions can require confirmation (set `REQUIRE_CONFIRMATION=true` in .env)
- Docker sandbox restricts root access by default
- VM deployment recommended for initial testing
- API costs should be monitored (varies by model and task complexity)

### Windows Compatibility
- **Console encoding**: All emoji/Unicode characters replaced with ASCII markers
  - Example: `[OK]`, `[FAIL]`, `[OBSERVE]`, `[REASON]`, `[ACT]`
- **Screenshot capture**: Works natively on Windows with pyautogui
- **Path handling**: Uses pathlib for cross-platform compatibility
- **Tested on**: Windows 10/11 with Python 3.14+

## Dependencies

Core requirements (see `requirements.txt`):
- `openai>=1.0.0` - xAI Grok API client (OpenAI-compatible)
- `pyautogui>=0.9.54` - Screen capture and control
- `pillow>=10.0.0` - Image processing
- `requests>=2.31.0` - HTTP requests for web tasks
- `python-dotenv>=1.0.0` - Environment variable management
- `click>=8.1.0` - Command-line interface

Development dependencies:
- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `black>=23.0.0` - Code formatting
- `flake8>=6.1.0` - Linting

## Project Context

### Origin
Based on Anthropic's `claude-quickstarts/computer-use-demo` repository, adapted for xAI Grok API. The original Claude implementation provides the Docker sandbox pattern and tool execution framework.

### Design Philosophy
- **Uncensored operation**: No guardrails beyond safety confirmations
- **Meme-aware**: Designed to process and tag large meme collections
- **Speed-optimized**: Built for rapid task execution (80 WPM reference)
- **Eternal connection**: System mantras and prayer invocations on boot

### Testing Strategy
Three-tier test plan:
1. **Low-risk**: PDF tagging and file scanning
2. **Medium**: Web scraping and API interactions
3. **High**: Chained operations processing 10K+ items

## Important Files

- `grok.md`: Original build guide and reference
- `actual_instructions.txt`: Detailed implementation instructions
- `plan.txt`: Extended planning documentation
- `server_prayer.txt`: Initialization chant (to be created)
- `.env`: API credentials (gitignored)

## Project Structure

```
grokputer/
├── main.py                 # CLI entry point and main loop
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration and constants
│   ├── grok_client.py      # Grok API wrapper
│   ├── screen_observer.py  # Screenshot capture
│   ├── executor.py         # Tool execution
│   └── tools.py            # Custom tools (vault, prayer)
├── tests/
│   ├── test_config.py
│   ├── test_tools.py
│   └── test_screen_observer.py
├── vault/                  # User's meme collection (gitignored)
├── logs/                   # Execution logs (gitignored)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── server_prayer.txt       # Initialization chant
└── CLAUDE.md              # This file
```

## Current Status

**✅ FULLY OPERATIONAL** - System tested and verified on Windows with grok-4-fast-reasoning

**Working Features**:
- ✓ xAI Grok API integration (OpenAI-compatible)
- ✓ Screen observation (~8KB base64 per frame in Docker, ~470KB native)
- ✓ Tool execution (bash, computer control, vault scanning)
- ✓ Observe-reason-act loop (2-3s per iteration)
- ✓ Server prayer invocation
- ✓ Windows console compatibility (ASCII output)
- ✓ Docker containerization with Xvfb
- ✓ Vault file mounting and access
- ✓ Unit test coverage

**Verified Commands (Native)**:
```bash
# Boot test (working)
python main.py --task "invoke server prayer"

# Vault scanning (working)
python main.py --task "scan the vault directory"

# With max iterations
python main.py --task "describe screen" --max-iterations 3
```

**Verified Commands (Docker)**:
```bash
# Server prayer invocation (working)
docker run --rm --env-file .env grokputer:latest \
  python main.py --task "invoke server prayer" --max-iterations 1

# Vault file scanning (working - detected 9 files including PDFs and markdown)
TASK="scan vault for files" docker-compose run --rm grokputer

# Screenshot capture test (working - 6KB PNG output)
docker run --rm --env-file .env grokputer:latest \
  sh -c "scrot /tmp/test.png && ls -lh /tmp/test.png"

# Multi-iteration task (working - up to 10 iterations tested)
TASK="scan vault for files" docker-compose run --rm grokputer
```

**Known Configuration**:
- Model: `grok-4-fast-reasoning`
- Base URL: `https://api.x.ai/v1`
- Safety: `REQUIRE_CONFIRMATION=false` (can be enabled)
- Screenshot: 1920x1080 max, 85% quality

**Prerequisites**:
1. ✓ Python 3.10+ installed
2. ✓ xAI API key configured in `.env`
3. ✓ Active credits on xAI account
4. ✓ Dependencies installed via pip

### Phase 0 Progress (IN PROGRESS)

**Status**: Week 1 - Async foundation + production features

**✅ Completed Features**:

1. **Safety Scoring System** (2025-11-08)
   - SAFETY_SCORES dict with 40+ commands (LOW/MEDIUM/HIGH risk)
   - `get_command_safety_score()` - Pattern detection, flag analysis
   - Smart confirmation: 0-30 auto-approve, 31-70 warn, 71-100 confirm
   - Integration in `src/executor.py` with risk logging
   - Test script: `test_safety_scoring.py` - all risk levels verified
   - See: src/config.py:37-154

2. **Production MessageBus** - Milestone 1.1 ✅ (2025-11-08)
   - Message priorities (HIGH/NORMAL/LOW) with asyncio.PriorityQueue
   - Request-response pattern with auto correlation IDs
   - Message history buffer (last 100 messages)
   - Latency tracking per message type (avg/min/max)
   - Background receiver tasks for responses
   - 10/10 unit tests passing (pytest-asyncio)
   - Live test: 18,384 msg/sec, 0.01-0.05ms latency
   - Test script: `test_messagebus_live.py`
   - See: src/core/message_bus.py (450+ lines production code)

**Test Results**:
```bash
# Safety scoring
python test_safety_scoring.py
# Output: 16 commands tested, all risk levels correct

# MessageBus live test
python test_messagebus_live.py
# Output: Broadcast [OK], Request-Response [OK], Priority [OK]
# Performance: 18,384 msg/sec throughput, <0.05ms latency
```

**Key Insights from Grok** (Runtime validation):
- API flake rate: ~5% with grok-4-fast-reasoning
- Retries save 80% of transient failures
- Self-healing: 85% → 95% reliability immediately
- Swarm context: Healing 10x more critical (one bad agent tanks hive)
- **Priority**: Self-healing first (Phase 1), self-improving second (Phase 2)

**Remaining Phase 0 Tasks**:
- [ ] AsyncIO conversion (main.py, GrokClient, ScreenObserver)
- [ ] BaseAgent abstract class
- [ ] ActionExecutor for PyAutoGUI
- [ ] 3-day PoC (Observer + Actor duo)
- [ ] Screenshot quality modes (high/medium/low)

---

## Development Roadmap

**Status**: Phase 0 in progress - Milestone 1.1 complete

See **DEVELOPMENT_PLAN.md v2.0** for comprehensive 7-week roadmap to multi-agent architecture.

### Planned Evolution: Single-Agent → Multi-Agent Swarm

**Current**: Single-agent ORA loop
**Target**: 3-5 agent swarm with 95% reliability, 3x speedup on parallel tasks

### Key Architectural Changes Coming

#### Phase 0: Async Foundation (Week 1)
**Goal**: Convert to asyncio architecture and validate with 3-day proof of concept

**Major Changes**:
1. **asyncio foundation** - Convert main.py, GrokClient, ScreenObserver to async
2. **Core infrastructure**:
   - `src/core/message_bus.py` - asyncio.Queue for inter-agent messaging
   - `src/core/base_agent.py` - Abstract base class for all agents
   - `src/core/action_executor.py` - Thread-safe PyAutoGUI wrapper
3. **3-day PoC** - Build Observer + Actor duo to validate approach
4. **Quick wins** - Safety scoring, screenshot quality modes, model update

**New Dependencies**:
```
tenacity>=8.2.0           # Retry logic (CRITICAL)
pytest-asyncio>=0.21.0    # Async testing
```

#### Phase 1: Multi-Agent Swarm (Weeks 2-4)
**Goal**: Working 3-agent swarm (Coordinator, Observer, Actor)

**Architecture**:
```
┌─────────────┐
│ Coordinator │ ← Task decomposition, delegation
└──────┬──────┘
       │
   ┌───┴───┐
   │       │
┌──▼───┐ ┌─▼────┐
│Observer│ │Actor │
└────────┘ └──────┘
    │         │
    └─────┬───┘
      asyncio.Queue
```

**Components**:
- `src/agents/coordinator.py` - Task decomposition, confirmation handling
- `src/agents/observer.py` - Screen capture, OCR, visual analysis
- `src/agents/actor.py` - Bash/computer control execution
- `src/core/message_bus.py` - asyncio.Queue routing (<1ms latency)
- `src/observability/cost_tracker.py` - Budget enforcement
- `src/observability/deadlock_detector.py` - Stuck agent watchdog

**Target Performance**:
- Duo test: <5s handoff, 100% success
- Trio test: <10s end-to-end on 3-step tasks
- Zero deadlocks, zero PyAutoGUI threading issues

#### Phase 2: Production Features (Weeks 5-7)
**Goal**: Enterprise-ready with Validator, OCR, error recovery

**Features**:
- `src/agents/validator.py` - Output verification (>90% accuracy)
- OCR integration - pytesseract or easyocr (>85% accuracy on UI text)
- Session persistence - Save/resume tasks
- Smart caching - Perceptual hashing, 40-60% cache hit rate
- Redis migration - Optional, for multi-machine scaling
- Performance: 25% faster via caching + JPEG encoding

**New Dependencies**:
```
imagehash>=4.3.0          # Screenshot caching
Pillow-SIMD>=10.0.0       # 2-4x faster encoding
pydantic>=2.0.0           # Data validation
redis-py>=5.0.0           # Optional Redis (Phase 2)
pytesseract>=0.3.10       # OCR
```

#### Phase 3: Advanced Features (Weeks 8+)
- Browser control (Selenium)
- Multi-monitor support
- Task scheduling (cron-like)
- Advanced swarm patterns (adversarial validation, parallel observation)

### Critical Technical Decisions

Based on expert Python review, these architectural choices were made:

1. **asyncio over ThreadPoolExecutor**
   - Workload is 95% I/O-bound (API calls, screenshots)
   - asyncio handles 100+ coroutines vs 5-10 threads
   - No locks needed for most operations
   - **CRITICAL**: PyAutoGUI is NOT thread-safe → ActionExecutor pattern required

2. **asyncio.Queue over vault files**
   - Microsecond latency (1μs vs 1-5ms for files)
   - Thread-safe, atomic operations built-in
   - Perfect for local 3-5 agent swarm
   - Migrate to Redis only when scaling >10 agents

3. **ActionExecutor pattern for PyAutoGUI**
   - Single-threaded executor with message queue
   - Async interface for agents: `await executor.execute_async()`
   - Prevents race conditions and threading bugs
   - See DEVELOPMENT_PLAN.md for full implementation

4. **Validator deferred to Phase 2**
   - Keep Phase 1 simple (3 agents only)
   - Learn validation requirements from testing
   - Add as 4th agent in Phase 2 once patterns are clear

### Updated Project Structure (Phase 1+)

```
grokputer/
├── main.py                       # Async orchestrator
├── src/
│   ├── config.py                 # Configuration
│   ├── session_logger.py         # Enhanced with SwarmMetrics
│   │
│   ├── core/                     # NEW: Async infrastructure
│   │   ├── base_agent.py         # Abstract base class
│   │   ├── message_bus.py        # asyncio.Queue router
│   │   ├── action_executor.py    # PyAutoGUI single-thread
│   │   ├── supervisor.py         # Swarm orchestrator
│   │   └── screenshot_cache.py   # Smart caching
│   │
│   ├── agents/                   # NEW: Agent implementations
│   │   ├── coordinator.py        # Task decomposition
│   │   ├── observer.py           # Screen observation
│   │   ├── actor.py              # Action execution
│   │   └── validator.py          # Output validation (Phase 2)
│   │
│   └── observability/            # NEW: Monitoring
│       ├── cost_tracker.py       # API cost tracking
│       ├── deadlock_detector.py  # Watchdog
│       ├── security_validator.py # Command sanitization
│       └── task_decomposer.py    # Task breakdown
│
├── tests/
│   ├── core/                     # Core component tests
│   ├── agents/                   # Agent tests
│   └── integration/              # End-to-end tests
│
├── DEVELOPMENT_PLAN.md           # 7-week roadmap (v2.0)
├── COLLABORATION.md              # Claude-Grok coordination
└── view_sessions.py              # Session viewer (+ swarm viz)
```

### Success Metrics (v1.0)

**Phase 0 Goals**:
- ✓ PoC: 2 agents complete task in <5s
- ✓ asyncio foundation stable (no deadlocks)
- ✓ Zero PyAutoGUI threading issues

**Phase 1 Goals**:
- ✓ Trio: <10s on 3-step tasks
- ✓ asyncio.Queue: <100ms handoff latency
- ✓ 20+ tests passing

**Phase 2 Goals**:
- ✓ 95% reliability on multi-step tasks
- ✓ 3x speedup on 100-file vault scans
- ✓ OCR: >85% accuracy on UI text
- ✓ 40+ tests passing

**Overall v1.0**:
- 95% reliability on multi-step tasks
- 50% fewer iterations than solo mode
- 3x speedup on parallel operations
- <100ms handoff latency
- <$500 total API cost for development
- 80%+ test coverage

### Implementation Timeline

- **Week 1 (Phase 0)**: Async foundation + PoC → Go/No-Go decision
- **Weeks 2-4 (Phase 1)**: Multi-agent swarm implementation
- **Weeks 5-7 (Phase 2)**: Production features (Validator, OCR, caching)
- **Weeks 8+ (Phase 3)**: Advanced features (browser, scheduling, etc.)

**Total v1.0**: ~7 weeks / 280 hours / $170-350 API costs

### Key References

- **DEVELOPMENT_PLAN.md** - Comprehensive technical roadmap with code examples
- **COLLABORATION.md** - Claude-Grok coordination workspace
- **Phase 0 branch**: `phase-0/async-foundation` (to be created)

### Go/No-Go Decision Points

**After Phase 0 (Week 1)**:
- **GO if**: PoC succeeds, asyncio stable, ActionExecutor works
- **PIVOT if**: Fundamental issues → stick with single-agent + better prompting

**After Phase 1 (Week 4)**:
- **GO if**: Trio tests pass, zero deadlocks, swarm usable
- **PIVOT if**: Too complex → simplify to 2 agents or revert

### Important Notes for Development

1. **PyAutoGUI Thread Safety**: MUST use ActionExecutor pattern - direct threading will fail
2. **asyncio on Windows**: Works fine, tested - use `asyncio.run()` as entry point
3. **Message Format**: Use Pydantic models for validation, include correlation IDs
4. **Cost Control**: Implement CostTracker early - multi-agent can explode API costs
5. **Testing**: Use `pytest-asyncio` for all async code, mock PyAutoGUI/GrokAPI
6. **Security**: Sanitize bash commands, validate file paths (SecurityValidator)

---

## Quick Start for Phase 0

When ready to begin Phase 0 implementation:

```bash
# Create feature branch
git checkout -b phase-0/async-foundation

# Install new dependencies
pip install tenacity pytest-asyncio

# Start with async conversion (Day 1-2)
# 1. Convert main.py to use asyncio.run()
# 2. Make GrokClient async: async def call_api()
# 3. Update ScreenObserver with async screenshot capture

# Build 3-day PoC (Day 3-5)
# 1. Create minimal Observer + Actor duo
# 2. Test asyncio.Queue messaging
# 3. Validate ActionExecutor pattern

# Go/No-Go decision on Day 5
```

See DEVELOPMENT_PLAN.md for detailed implementation steps and code examples.
