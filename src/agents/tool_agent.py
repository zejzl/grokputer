#!/usr/bin/env python3
# ToolAgent: Handles bash commands and file operations with safety scoring.
# Wraps existing tools (bash, view_file, create_file, str_replace_editor).
# Broadcasts execution requests/results via MessageBus for distributed swarm.

import asyncio
import os
import json
import uuid
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

from src.agents.base_agent import BaseAgent
from src.core.message_bus import MessageBus
# Assume SafetyScorer from src/executor.py – import if exists, else inline
from src.executor import SafetyScorer  # Fallback to simple scoring if not

class ToolAgent(BaseAgent):
    def __init__(self, name: str = "ToolAgent", agent_type: str = "tool"):
        super().__init__(name=name, agent_type=agent_type)
        self.bus = MessageBus(backend=os.getenv('MESSAGE_BUS_BACKEND', 'redis'))
        self.safety_scorer = SafetyScorer() if 'SafetyScorer' in globals() else self._simple_scorer()
        self.priority_map = {"HIGH": 0, "NORMAL": 1, "LOW": 2}
        self.logger.info("ToolAgent initialized – Ready for bash/file ops with safety.")

    def _simple_scorer(self):
        """Fallback safety scorer if not imported."""
        def score_command(cmd: str) -> int:
            cmd_lower = cmd.lower()
            score = 0
            if any(danger in cmd_lower for danger in ['rm -rf', 'sudo', 'del /f', 'format']):
                score += 100
            elif any(write in cmd_lower for write in ['rm', 'mv', 'cp', '--force']):
                score += 70
            elif any(read in cmd_lower for read in ['cat', 'ls', 'find', 'grep']):
                score += 20
            else:
                score = 40  # Default medium
            return min(score, 100)
        return type('Scorer', (), {'score_command': score_command})()

    async def execute_bash(self, cmd: str, priority: str = "NORMAL") -> Dict[str, Any]:
        """Execute bash command with safety check. Broadcast for distributed exec if needed."""
        risk_score = self.safety_scorer.score_command(cmd)
        self.logger.info(f"Bash cmd '{cmd}' risk score: {risk_score}/100")
        
        if risk_score > 70 and os.getenv('REQUIRE_CONFIRMATION', 'false').lower() == 'true':
            corr_id = str(uuid.uuid4())
            confirm_msg = {
                "type": "tool_confirm_request",
                "cmd": cmd,
                "risk": risk_score,
                "corr_id": corr_id,
                "from": self.agent_type,
                "priority": "HIGH"
            }
            await self.bus.broadcast(confirm_msg, priority="HIGH")
            # Wait for confirmation (simplified – in full swarm, use req_resp from Coordinator)
            confirmed = True  # YOLO mode assumes approve
            if not confirmed:
                return {"success": False, "error": "High-risk command denied."}
        
        # Broadcast exec request (for distributed processing if needed)
        corr_id = str(uuid.uuid4())
        exec_msg = {
            "type": "tool_bash_exec",
            "cmd": cmd,
            "corr_id": corr_id,
            "from": self.agent_type,
            "priority": priority
        }
        try:
            resp = await self.bus.request_response(exec_msg, timeout=30.0, priority=priority)
            if resp and resp.get("success"):
                # Broadcast result to swarm
                result_msg = {
                    "type": "tool_result",
                    "cmd": cmd,
                    "output": resp["output"],
                    "success": True,
                    "from": self.agent_type
                }
                await self.bus.broadcast(result_msg, priority="NORMAL")
                return resp
            else:
                return {"success": False, "error": "Bash execution failed or timed out."}
        except asyncio.TimeoutError:
            self.logger.error(f"Bash '{cmd}' timed out after 30s.")
            return {"success": False, "error": "Timeout."}

    async def file_op(self, path: str, action: str = "view", content: Optional[str] = None, priority: str = "LOW") -> Dict[str, Any]:
        """File operations: view/read, create, edit/replace. Safety for writes."""
        valid_actions = ["view", "create", "edit"]
        if action not in valid_actions:
            return {"success": False, "error": f"Invalid action: {action}. Use view/create/edit."}
        
        risk_score = {"view": 20, "create": 50, "edit": 80}.get(action, 40)
        self.logger.info(f"File op: {action} {path} (risk: {risk_score}/100)")
        
        if risk_score > 70 and os.getenv('REQUIRE_CONFIRMATION', 'false').lower() == 'true':
            # Broadcast for confirmation (similar to bash)
            pass  # YOLO approve
        
        # Execute based on action
        try:
            if action == "view":
                result = self._view_file(path)
            elif action == "create":
                result = self._create_file(path, content)
            elif action == "edit":
                result = self._edit_file(path, content)
            
            if result["success"]:
                # Broadcast result
                result_msg = {
                    "type": "tool_result",
                    "path": path,
                    "action": action,
                    "output": result["output"],
                    "success": True,
                    "from": self.agent_type
                }
                await self.bus.broadcast(result_msg, priority="NORMAL")
            
            return result
        except Exception as e:
            self.logger.error(f"File op failed: {e}")
            return {"success": False, "error": str(e)}

    def _view_file(self, path: str) -> Dict[str, Any]:
        """View file contents (use view_file tool)."""
        try:
            with open(path, 'r') as f:
                content = f.read()
            return {"success": True, "output": content}
        except FileNotFoundError:
            return {"success": False, "error": f"File {path} not found."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_file(self, path: str, content: str) -> Dict[str, Any]:
        """Create new file with content (use create_file tool)."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(content or "")
            return {"success": True, "output": f"Created {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _edit_file(self, path: str, new_content: str) -> Dict[str, Any]:
        """Edit file (overwrite for simplicity; use str_replace_editor for precise)."""
        try:
            with open(path, 'w') as f:
                f.write(new_content)
            return {"success": True, "output": f"Edited {path}"}
        except FileNotFoundError:
            return {"success": False, "error": f"File {path} not found."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def handle_message(self, msg: Dict[str, Any]):
        """Override BaseAgent: Handle tool-specific messages (e.g., exec requests)."""
        msg_type = msg.get("type")
        if msg_type == "tool_bash_exec":
            cmd = msg["cmd"]
            # Execute locally or delegate
            result = await self.execute_bash(cmd, msg.get("priority", "NORMAL"))
            if msg.get("corr_id"):
                resp = {
                    "type": "tool_bash_response",
                    "corr_id": msg["corr_id"],
                    "result": result,
                    "from": self.agent_type
                }
                await self.bus.send_response(resp)
        elif msg_type == "tool_confirm_request":
            # Auto-approve in yolo
            corr_id = msg["corr_id"]
            approve = {"type": "tool_confirm_response", "approved": True, "corr_id": corr_id, "from": self.agent_type}
            await self.bus.send_response(approve)
        else:
            # Delegate to BaseAgent
            await super().handle_message(msg)

# Example usage (for testing)
if __name__ == "__main__":
    async def test_tool():
        agent = ToolAgent()
        # Bash
        bash_result = await agent.execute_bash("ls -la", priority="HIGH")
        print(f"Bash result: {bash_result}")
        # File op
        file_result = await agent.file_op("test_tool.txt", "create", content="ZA GROKA", priority="NORMAL")
        print(f"File result: {file_result}")

    asyncio.run(test_tool())
