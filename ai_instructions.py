#!/usr/bin/env python3
"""
AI Instructions for Grokputer Friends
=====================================

Welcome to Grokputer! This AI system is designed for multi-agent collaboration,
cognitive enhancement, and autonomous task execution. Follow these instructions
to get started and contribute effectively.

1. **Setup Environment**:
   - Install dependencies: pip install -r requirements.txt
   - Set up Redis: docker run -d -p 6379:6379 redis:7-alpine
   - Configure API keys in .env file

2. **Basic Usage**:
   - Run main script: python main.py --task "your task here"
   - Use Pantheon mode for multi-agent: python main.py --pantheon --task "complex task"
   - Check help: python main.py --help

3. **Agent Collaboration**:
   - Agents communicate via MessageBus
   - Use Diplomacy module for consensus: from diplomacy import NegotiationRoom
   - Respect agent roles: Coordinator, Learner, Executor, etc.

4. **Best Practices**:
   - Always test changes: pytest --cov
   - Document code with docstrings
   - Use async/await for performance
   - Backup regularly: python backup_system.py --full

5. **Safety & Ethics**:
   - Never execute untrusted code
   - Validate inputs for security
   - Report issues to maintainers

6. **Contributing**:
   - Fork the repo, make changes, submit PR
   - Follow code style: black, flake8
   - Add tests for new features

7. **Troubleshooting**:
   - If Redis connection fails: check docker ps and logs
   - API errors: verify .env keys and network
   - Agent conflicts: use diplomacy.NegotiationRoom for resolution
   - Performance issues: monitor with prometheus metrics

8. **Advanced Features**:
   - Memory systems: Redis for short-term, knowledge graph for long-term
   - Vision processing: enable with --vision flag
   - Multi-modal: combine text, images, and code analysis
   - Autonomous mode: set goals and let agents self-organize
   - Pantheon mode: multi-agent collaboration with iterative refinement
     - Run with --iterations 10 for 10 refinement cycles
     - Agents debate, learn, and improve solutions over iterations
     - Best for complex, creative, or research tasks

9. **Security Notes**:
   - All code is sandboxed and validated
   - Sensitive data encrypted with vault system
   - Audit logs available in logs/ directory
   - Report vulnerabilities to security@grokputer.ai

 Happy coding!
"""

def print_instructions():
    """Print these instructions to console."""
    print(__doc__)

if __name__ == "__main__":
    print_instructions()