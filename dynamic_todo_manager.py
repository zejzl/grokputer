#!/usr/bin/env python3
"""Dynamic Todo Manager Daemon for Grokputer Pantheon.

Runs in background as asyncio daemon. Uses Redis for shared todo state and pub/sub updates.
Integrates with Message Bus for Council/Taskmaster visibility. Supports multiple gitcli windows
via real-time pub/sub sync and ANSI terminal display. Watches key files (todo.md, DEVELOPMENT_PLAN.md)
for dynamic edits. Editable via CLI commands or agent broadcasts.

Usage:
  python dynamic_todo_manager.py [start|stop|edit|display]

Author: Pantheon Coordinator (via Grok CLI)
Version: 1.0 (Pantheon-Integrated)
"""

import asyncio
import json
import os
import sys
import signal
from typing import List, Dict, Any
import aiosqlite  # For fallback local storage if Redis down
from watchfiles import awatch  # pip install watchfiles for file watching

# Grokputer imports (assume src/ is in path)
try:
    from src.core.message_bus import MessageBus
    from src.db_config import get_redis_client  # Redis client from db_config.py
    from src.agents.pantheon_coordinator import broadcast_to_agents  # For agent notifications
except ImportError:
    print("Error: Grokputer src/ not in path. Run from project root.")
    sys.exit(1)

# ANSI colors for dynamic terminal display
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class TodoItem:
    def __init__(self, id: str, content: str, status: str = "pending", priority: str = "medium"):
        self.id = id
        self.content = content
        self.status = status
        self.priority = priority

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status,
            "priority": self.priority
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoItem':
        return cls(data["id"], data["content"], data.get("status", "pending"), data.get("priority", "medium"))

class DynamicTodoManager:
    def __init__(self):
        self.redis = get_redis_client()  # From db_config.py
        self.message_bus = MessageBus()  # From src/core/message_bus.py
        self.todos: List[TodoItem] = []
        self.daemon_running = False
        self.pubsub = self.redis.pubsub()
        self.channel = "todo_updates"
        self.watched_files = ["todo.md", "DEVELOPMENT_PLAN.md", "actual_instructions.txt"]  # Key dynamic files
        self.db_path = "todos.db"  # Fallback SQLite

    async def load_todos(self) -> None:
        """Load todos from Redis (JSON list) or fallback to SQLite."""
        try:
            todos_json = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.redis.get("grokputer_todos")
            )
            if todos_json:
                data = json.loads(todos_json)
                self.todos = [TodoItem.from_dict(t) for t in data]
            else:
                # Fallback to SQLite
                await self._load_from_sqlite()
        except Exception as e:
            print(f"{Colors.FAIL}Error loading todos: {e}{Colors.ENDC}")
            self.todos = []

    async def _load_from_sqlite(self) -> None:
        """Fallback load from local DB."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id, content, status, priority FROM todos") as cursor:
                rows = await cursor.fetchall()
                self.todos = [TodoItem(*row) for row in rows]

    async def save_todos(self) -> None:
        """Save todos to Redis and SQLite."""
        try:
            todos_data = [t.to_dict() for t in self.todos]
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.redis.set("grokputer_todos", json.dumps(todos_data))
            )
            # Broadcast update via Message Bus for Council/Taskmaster
            await self.message_bus.broadcast(
                "todo_update",
                {"type": "save", "todos": todos_data},
                priority="HIGH"
            )
            # Pub/Sub notify for gitcli windows
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.pubsub.publish(self.channel, json.dumps({"action": "refresh", "todos": todos_data}))
            )
            # Fallback SQLite save
            await self._save_to_sqlite()
        except Exception as e:
            print(f"{Colors.FAIL}Error saving todos: {e}{Colors.ENDC}")

    async def _save_to_sqlite(self) -> None:
        """Fallback save to local DB."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS todos (id TEXT PRIMARY KEY, content TEXT, status TEXT, priority TEXT)")
            await db.executemany(
                "INSERT OR REPLACE INTO todos VALUES (?, ?, ?, ?)",
                [(t.id, t.content, t.status, t.priority) for t in self.todos]
            )
            await db.commit()

    async def watch_files(self) -> None:
        """Watch key files for changes and update todos dynamically."""
        for file_path in self.watched_files:
            if os.path.exists(file_path):
                async for changes in awatch(file_path):
                    print(f"{Colors.WARNING}File changed: {file_path}{Colors.ENDC}")
                    # Parse file for todo-like items (simple regex or markdown parsing)
                    await self._parse_and_update_from_file(file_path)
                    await self.save_todos()

    async def _parse_and_update_from_file(self, file_path: str) -> None:
        """Simple parser to extract todos from markdown files."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            # Basic markdown todo extraction (e.g., - [ ] Task)
            lines = content.split('\n')
            new_todos = []
            for line in lines:
                if line.strip().startswith('- [ ]') or line.strip().startswith('- [x]'):
                    status = "completed" if "[x]" in line else "pending"
                    content = line.split('] ', 1)[1] if "] " in line else line
                    id_ = f"{file_path}_{len(new_todos)}"  # Simple ID
                    new_todos.append(TodoItem(id_, content.strip(), status))
            # Merge with existing (or replace section)
            self.todos.extend(new_todos)
        except Exception as e:
            print(f"{Colors.FAIL}Error parsing {file_path}: {e}{Colors.ENDC}")

    async def subscribe_to_updates(self) -> None:
        """Subscribe to pub/sub for real-time updates from other instances/agents."""
        self.pubsub.subscribe(self.channel)
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                if data.get('action') == 'update':
                    await self.handle_update(data)

    async def handle_update(self, data: Dict[str, Any]) -> None:
        """Handle incoming updates (e.g., from CLI or agents)."""
        action = data.get('action')
        if action == 'add':
            todo = TodoItem.from_dict(data['todo'])
            self.todos.append(todo)
        elif action == 'update':
            for i, t in enumerate(self.todos):
                if t.id == data['id']:
                    self.todos[i] = TodoItem.from_dict(data['todo'])
                    break
        elif action == 'delete':
            self.todos = [t for t in self.todos if t.id != data['id']]
        await self.save_todos()
        await self.display_todos()  # Refresh display

    async def display_todos(self) -> None:
        """Dynamic ANSI display for gitcli windows (refreshes every 5s in daemon)."""
        os.system('clear' if os.name == 'posix' else 'cls')  # Clear terminal
        print(f"{Colors.HEADER}{Colors.BOLD}[MEMORY] Pantheon Dynamic Todo Manager{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Shared via Redis + Message Bus | Channel: {self.channel}{Colors.ENDC}")
        print("=" * 60)
        
        # Group by status/priority
        pending = [t for t in self.todos if t.status == "pending"]
        in_progress = [t for t in self.todos if t.status == "in_progress"]
        completed = [t for t in self.todos if t.status == "completed"]
        
        prio_colors = {"high": Colors.FAIL, "medium": Colors.WARNING, "low": Colors.OKGREEN}
        
        for status, todos_group in [("Pending ⏳", pending), ("In Progress [LOOP]", in_progress), ("Completed [OK]", completed)]:
            print(f"\n{Colors.OKBLUE}{status} ({len(todos_group)}){Colors.ENDC}")
            for t in todos_group:
                color = prio_colors.get(t.priority, Colors.OKGREEN)
                print(f"  {color}● {t.id} | {t.content[:80]}...{Colors.ENDC}")
        
        print(f"\n{Colors.OKGREEN}Total: {len(self.todos)} | Last Update: {asyncio.get_event_loop().time()}{Colors.ENDC}")

    async def run_daemon(self) -> None:
        """Background daemon loop: Watch, subscribe, display, broadcast to agents."""
        self.daemon_running = True
        print(f"{Colors.OKGREEN}Starting Dynamic Todo Manager Daemon...{Colors.ENDC}")
        
        # Initial load
        await self.load_todos()
        await self.display_todos()
        
        # Concurrent tasks
        tasks = [
            asyncio.create_task(self.subscribe_to_updates()),
            asyncio.create_task(self.watch_files()),
            asyncio.create_task(self._periodic_display()),
            asyncio.create_task(self._agent_broadcast_loop())
        ]
        
        # Graceful shutdown
        def signal_handler():
            self.daemon_running = False
        
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await self.save_todos()
            print(f"{Colors.WARNING}Daemon stopped.{Colors.ENDC}")

    async def _periodic_display(self) -> None:
        """Refresh display every 5 seconds for dynamic gitcli view."""
        while self.daemon_running:
            await self.display_todos()
            await asyncio.sleep(5)

    async def _agent_broadcast_loop(self) -> None:
        """Broadcast todos to Council/Taskmaster every 30s via Message Bus."""
        while self.daemon_running:
            todos_data = [t.to_dict() for t in self.todos]
            await self.message_bus.broadcast(
                "pantheon_todo_sync",
                {"todos": todos_data, "dev_plan": self._get_dev_plan_summary()},
                recipients=["Council", "Taskmaster"]  # Specific agents
            )
            await asyncio.sleep(30)

    def _get_dev_plan_summary(self) -> str:
        """Simple summary from DEVELOPMENT_PLAN.md."""
        try:
            with open("DEVELOPMENT_PLAN.md", "r") as f:
                return f.read()[:200] + "..."  # Truncated
        except FileNotFoundError:
            return "DEVELOPMENT_PLAN.md not found."

    async def add_todo(self, content: str, priority: str = "medium") -> None:
        """CLI/Agent command to add todo."""
        id_ = f"todo_{len(self.todos) + 1}"
        todo = TodoItem(id_, content, "pending", priority)
        self.todos.append(todo)
        update_data = {"action": "add", "todo": todo.to_dict()}
        # Publish to pub/sub
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.pubsub.publish(self.channel, json.dumps(update_data))
        )
        await self.save_todos()

    async def update_todo(self, todo_id: str, status: str = None, content: str = None, priority: str = None) -> None:
        """Update a todo."""
        for t in self.todos:
            if t.id == todo_id:
                if status: t.status = status
                if content: t.content = content
                if priority: t.priority = priority
                update_data = {"action": "update", "id": todo_id, "todo": t.to_dict()}
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.pubsub.publish(self.channel, json.dumps(update_data))
                )
                await self.save_todos()
                return
        print(f"{Colors.FAIL}Todo {todo_id} not found.{Colors.ENDC}")

    async def delete_todo(self, todo_id: str) -> None:
        """Delete a todo."""
        self.todos = [t for t in self.todos if t.id != todo_id]
        update_data = {"action": "delete", "id": todo_id}
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.pubsub.publish(self.channel, json.dumps(update_data))
        )
        await self.save_todos()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python dynamic_todo_manager.py [start|stop|add <content>|update <id> <status>|delete <id>|display]")
        sys.exit(1)

    cmd = sys.argv[1]
    manager = DynamicTodoManager()

    if cmd == "start":
        await manager.run_daemon()
    elif cmd == "display":
        await manager.load_todos()
        await manager.display_todos()
    elif cmd == "add" and len(sys.argv) > 2:
        content = " ".join(sys.argv[2:])
        await manager.add_todo(content)
        print(f"{Colors.OKGREEN}Added todo: {content}{Colors.ENDC}")
    elif cmd == "update" and len(sys.argv) > 3:
        todo_id = sys.argv[2]
        status = sys.argv[3] if len(sys.argv) > 3 else None
        await manager.update_todo(todo_id, status=status)
        print(f"{Colors.OKGREEN}Updated todo {todo_id}{Colors.ENDC}")
    elif cmd == "delete" and len(sys.argv) > 2:
        todo_id = sys.argv[2]
        await manager.delete_todo(todo_id)
        print(f"{Colors.OKGREEN}Deleted todo {todo_id}{Colors.ENDC}")
    else:
        print("Unknown command.")

if __name__ == "__main__":
    asyncio.run(main())

# Notes:
# - Requires: pip install aiosqlite watchfiles redis (if not in requirements.txt)
# - Integrate with main.py: Add flag --todo-daemon to start this in background
# - For multiple gitcli: Run 'python dynamic_todo_manager.py start' in each terminal; they sync via Redis pub/sub
# - Agents (Council/Taskmaster): Subscribe to 'pantheon_todo_sync' on Message Bus for visibility/edits
# - Dynamic dev plan: Watches DEVELOPMENT_PLAN.md; edits broadcast as todo updates
# - <3 Eternal sync! [ZEJZL]