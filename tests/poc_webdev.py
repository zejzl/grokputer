"""
Proof of Concept: WebDevAgent Demo

Demonstrates the WebDevAgent handling a complete web application development
workflow in the Grokputer multi-agent architecture.

Usage:
    python tests/poc_webdev.py

Author: Claude Code
Date: 2025-11-08
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.webdev_agent import WebDevAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.session_logger import SessionLogger


async def main():
    """Run WebDevAgent PoC demonstration."""
    print("\n" + "=" * 70)
    print("WebDevAgent PoC - Building a FastAPI Application")
    print("=" * 70 + "\n")

    start_time = time.time()

    # Initialize infrastructure
    print("[SETUP] Initializing MessageBus...")
    message_bus = MessageBus()

    print("[SETUP] Initializing SessionLogger...")
    from pathlib import Path
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    session_logger = SessionLogger(
        logs_dir=logs_dir,
        session_id=f"webdev_poc_{int(time.time())}"
    )

    # Create WebDevAgent
    print("[SETUP] Creating WebDevAgent (FastAPI + PostgreSQL + JWT)...\n")
    webdev_agent = WebDevAgent(
        agent_id="webdev",
        message_bus=message_bus,
        session_logger=session_logger,
        framework="fastapi",
        database="postgresql",
        auth_method="jwt"
    )

    # Register coordinator (simulated)
    message_bus.register_agent("coordinator")

    print("[OK] WebDevAgent ready!\n")

    # Workflow: Build a complete User Management API
    workflow_steps = [
        {
            "name": "Design Database Schema",
            "message_type": "design_database",
            "content": {
                "entities": [
                    {
                        "name": "User",
                        "fields": ["id", "email", "password_hash", "created_at", "is_active"]
                    },
                    {
                        "name": "Profile",
                        "fields": ["id", "user_id", "first_name", "last_name", "bio"]
                    }
                ],
                "relationships": [
                    {"from": "Profile", "to": "User", "type": "one-to-one"}
                ]
            }
        },
        {
            "name": "Setup JWT Authentication",
            "message_type": "setup_auth",
            "content": {
                "auth_type": "jwt"
            }
        },
        {
            "name": "Create API Endpoints",
            "message_type": "create_api",
            "content": {
                "specification": {
                    "endpoints": [
                        {"path": "/api/v1/users", "method": "GET", "description": "List users"},
                        {"path": "/api/v1/users", "method": "POST", "description": "Create user"},
                        {"path": "/api/v1/users/{id}", "method": "GET", "description": "Get user"},
                        {"path": "/api/v1/users/{id}", "method": "PUT", "description": "Update user"},
                        {"path": "/api/v1/users/{id}", "method": "DELETE", "description": "Delete user"},
                        {"path": "/api/v1/auth/login", "method": "POST", "description": "Login"},
                        {"path": "/api/v1/auth/logout", "method": "POST", "description": "Logout"}
                    ]
                }
            }
        },
        {
            "name": "Write Unit & Integration Tests",
            "message_type": "write_tests",
            "content": {
                "test_type": "unit",
                "coverage": 85
            }
        },
        {
            "name": "Review Code for Security",
            "message_type": "review_code",
            "content": {
                "code": """
async def create_user(user_data: dict):
    password = user_data['password']
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    user = User(email=user_data['email'], password_hash=hashed_password)
    db.add(user)
    await db.commit()
    return user
                """,
                "focus": "security"
            }
        },
        {
            "name": "Generate Docker Deployment",
            "message_type": "deploy_app",
            "content": {
                "platform": "docker"
            }
        }
    ]

    results = []

    # Execute workflow
    for i, step in enumerate(workflow_steps, 1):
        print(f"[STEP {i}/{len(workflow_steps)}] {step['name']}")

        message = Message(
            from_agent="coordinator",
            to_agent="webdev",
            message_type=step["message_type"],
            content=step["content"],
            priority=MessagePriority.NORMAL
        )

        step_start = time.time()
        result = await webdev_agent.process_message(message)
        step_duration = time.time() - step_start

        if result and result.get("status") == "success":
            print(f"  [OK] {result['message']} ({step_duration:.3f}s)")
            results.append({"step": step["name"], "result": result, "duration": step_duration})
        else:
            print(f"  [FAIL] {result.get('message', 'Unknown error')}")
            results.append({"step": step["name"], "result": result, "duration": step_duration})

        print()
        await asyncio.sleep(0.1)  # Small delay for readability

    # Get final agent status
    print("[STATUS] Checking agent status...")
    status_message = Message(
        from_agent="coordinator",
        to_agent="webdev",
        message_type="get_status",
        content={},
        priority=MessagePriority.NORMAL
    )
    status = await webdev_agent.process_message(status_message)
    print(f"  Agent State: {status.get('state', 'unknown')}")
    print(f"  Tasks Completed: {status.get('tasks_completed', 0)}")
    print()

    # Summary
    total_duration = time.time() - start_time
    print("=" * 70)
    print("WORKFLOW SUMMARY")
    print("=" * 70)
    print(f"Total Steps: {len(workflow_steps)}")
    print(f"Successful: {sum(1 for r in results if r['result'].get('status') == 'success')}")
    print(f"Failed: {sum(1 for r in results if r['result'].get('status') != 'success')}")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Average Step Duration: {total_duration / len(workflow_steps):.3f}s")
    print()

    # Detailed results
    print("DETAILED RESULTS:")
    print("-" * 70)
    for i, result_item in enumerate(results, 1):
        print(f"{i}. {result_item['step']}")
        print(f"   Status: {result_item['result'].get('status', 'unknown')}")
        print(f"   Duration: {result_item['duration']:.3f}s")
        if result_item['result'].get('status') == 'success':
            # Print key details
            result = result_item['result']
            if 'framework' in result:
                print(f"   Framework: {result['framework']}")
            if 'database' in result:
                print(f"   Database: {result['database']}")
            if 'auth_type' in result:
                print(f"   Auth Type: {result['auth_type']}")
            if 'files' in result:
                print(f"   Files Generated: {len(result['files'])}")
            if 'issues_found' in result:
                print(f"   Issues Found: {result['issues_found']}")
                print(f"   Security Score: {result['security_score']}/100")
        print()

    # Cleanup
    print("[CLEANUP] Stopping agent...")
    await webdev_agent.stop()
    print("[CLEANUP] Shutting down MessageBus...")
    await message_bus.shutdown()

    print("\n" + "=" * 70)
    print(f"[OK] PoC Complete - {total_duration:.2f}s total")
    print("=" * 70 + "\n")

    # Validation
    success = all(r['result'].get('status') == 'success' for r in results)
    print(f"[VALIDATION] All steps successful: {success}")
    print(f"[VALIDATION] Performance target (<10s): {total_duration < 10.0}")
    print()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
