"""
Community Vault Sync for Grokputer
Share and sync tools, agents, and configurations with the community.
Supports local file sync and cloud storage backends.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for vault storage backends."""

    @abstractmethod
    async def pull(self, local_path: Path, remote_path: str) -> bool:
        """Pull data from remote storage to local path."""
        pass

    @abstractmethod
    async def push(self, local_path: Path, remote_path: str) -> bool:
        """Push data from local path to remote storage."""
        pass

    @abstractmethod
    async def list_files(self, remote_path: str) -> List[str]:
        """List files in remote storage."""
        pass


class LocalFileBackend(StorageBackend):
    """Local file system storage backend."""

    def __init__(self, base_path: Path):
        self.base_path = base_path

    async def pull(self, local_path: Path, remote_path: str) -> bool:
        """Copy from local source to local destination."""
        remote_full_path = self.base_path / remote_path
        if remote_full_path.exists():
            import shutil

            if remote_full_path.is_file():
                shutil.copy2(remote_full_path, local_path)
            else:
                shutil.copytree(remote_full_path, local_path, dirs_exist_ok=True)
            return True
        return False

    async def push(self, local_path: Path, remote_path: str) -> bool:
        """Copy from local source to local destination."""
        remote_full_path = self.base_path / remote_path
        remote_full_path.parent.mkdir(parents=True, exist_ok=True)
        if local_path.is_file():
            import shutil

            shutil.copy2(local_path, remote_full_path)
        else:
            import shutil

            shutil.copytree(local_path, remote_full_path, dirs_exist_ok=True)
        return True

    async def list_files(self, remote_path: str) -> List[str]:
        """List files in local directory."""
        remote_full_path = self.base_path / remote_path
        if remote_full_path.exists() and remote_full_path.is_dir():
            return [str(f.relative_to(remote_full_path)) for f in remote_full_path.rglob("*") if f.is_file()]
        return []


class GitBackend(StorageBackend):
    """Git repository storage backend."""

    def __init__(self, repo_url: str, local_repo_path: Path):
        self.repo_url = repo_url
        self.local_repo_path = local_repo_path

    async def _ensure_repo(self) -> bool:
        """Ensure git repository exists and is up to date."""
        if not self.local_repo_path.exists():
            try:
                result = await self._run_git_command(["clone", self.repo_url, str(self.local_repo_path)])
                return result.returncode == 0
            except Exception as e:
                logger.error(f"Failed to clone repository: {e}")
                return False
        else:
            # Pull latest changes
            try:
                result = await self._run_git_command(["pull"], cwd=self.local_repo_path)
                return result.returncode == 0
            except Exception as e:
                logger.error(f"Failed to pull repository: {e}")
                return False

    async def _run_git_command(self, args: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Run a git command asynchronously."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
        )

    async def pull(self, local_path: Path, remote_path: str) -> bool:
        """Pull file/directory from git repository."""
        if not await self._ensure_repo():
            return False

        remote_full_path = self.local_repo_path / remote_path
        if remote_full_path.exists():
            import shutil

            if remote_full_path.is_file():
                shutil.copy2(remote_full_path, local_path)
            else:
                shutil.copytree(remote_full_path, local_path, dirs_exist_ok=True)
            return True
        return False

    async def push(self, local_path: Path, remote_path: str) -> bool:
        """Push file/directory to git repository."""
        if not await self._ensure_repo():
            return False

        # Copy file to repo
        repo_dest = self.local_repo_path / remote_path
        repo_dest.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        if local_path.is_file():
            shutil.copy2(local_path, repo_dest)
        else:
            shutil.copytree(local_path, repo_dest, dirs_exist_ok=True)

        # Commit and push
        try:
            await self._run_git_command(["add", remote_path], cwd=self.local_repo_path)
            await self._run_git_command(["commit", "-m", f"Sync {remote_path}"], cwd=self.local_repo_path)
            await self._run_git_command(["push"], cwd=self.local_repo_path)
            return True
        except Exception as e:
            logger.error(f"Failed to push to git: {e}")
            return False

    async def list_files(self, remote_path: str) -> List[str]:
        """List files in git repository."""
        if not await self._ensure_repo():
            return []

        remote_full_path = self.local_repo_path / remote_path
        if remote_full_path.exists() and remote_full_path.is_dir():
            return [str(f.relative_to(remote_full_path)) for f in remote_full_path.rglob("*") if f.is_file()]
        return []


class VaultSync:
    """
    Syncs community tools and configurations.
    Supports multiple storage backends for data persistence.
    """

    def __init__(
        self,
        vault_dir: Path = Path("vault"),
        community_dir: Path = Path("community"),
        storage_backend: Optional[StorageBackend] = None,
    ):
        self.vault_dir = vault_dir
        self.community_dir = community_dir
        self.logger = logger

        # Use provided backend or default to local file backend
        self.storage_backend = storage_backend or LocalFileBackend(community_dir)

        # Create community directory structure
        self.community_dir.mkdir(exist_ok=True)
        (self.community_dir / "tools").mkdir(exist_ok=True)
        (self.community_dir / "agents").mkdir(exist_ok=True)
        (self.community_dir / "configs").mkdir(exist_ok=True)
        (self.community_dir / "docs").mkdir(exist_ok=True)

    async def pull(self) -> Dict:
        """
        Pull latest community contributions from storage backend.
        """
        print("\n[VAULT SYNC] Pulling latest community contributions...")

        result = {"status": "success", "tools_updated": [], "agents_updated": [], "configs_updated": [], "new_items": 0}

        try:
            # Pull tools
            tools_files = await self.storage_backend.list_files("tools")
            for tool_file in tools_files:
                if tool_file.endswith(".py") and not tool_file.startswith("test_"):
                    local_path = self.community_dir / "tools" / tool_file
                    if not local_path.exists():
                        success = await self.storage_backend.pull(local_path, f"tools/{tool_file}")
                        if success:
                            result["tools_updated"].append(tool_file)
                            result["new_items"] += 1
                            print(f"  ✓ Tool: {tool_file}")

            # Pull agents
            agent_files = await self.storage_backend.list_files("agents")
            for agent_file in agent_files:
                if agent_file.endswith("_agent.py"):
                    local_path = self.community_dir / "agents" / agent_file
                    if not local_path.exists():
                        success = await self.storage_backend.pull(local_path, f"agents/{agent_file}")
                        if success:
                            result["agents_updated"].append(agent_file)
                            result["new_items"] += 1
                            print(f"  ✓ Agent: {agent_file}")

            # Pull docs
            docs_files = await self.storage_backend.list_files("docs")
            for doc_file in docs_files:
                if doc_file.endswith(".md"):
                    local_path = self.community_dir / "docs" / doc_file
                    if not local_path.exists():
                        success = await self.storage_backend.pull(local_path, f"docs/{doc_file}")
                        if success:
                            result["new_items"] += 1
                            print(f"  ✓ Doc: {doc_file}")

            # Pull configs
            config_files = await self.storage_backend.list_files("configs")
            for config_file in config_files:
                local_path = self.community_dir / "configs" / config_file
                if not local_path.exists():
                    success = await self.storage_backend.pull(local_path, f"configs/{config_file}")
                    if success:
                        result["configs_updated"].append(config_file)
                        result["new_items"] += 1
                        print(f"  ✓ Config: {config_file}")

        except Exception as e:
            self.logger.error(f"Pull operation failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        print(f"\n[VAULT SYNC] Pull complete!")
        print(f"  New items: {result['new_items']}")
        print(f"  Tools: {len(result['tools_updated'])}")
        print(f"  Agents: {len(result['agents_updated'])}")
        print(f"  Configs: {len(result['configs_updated'])}")

        return result

    async def push(self) -> Dict:
        """
        Push local contributions to community storage backend.
        """
        print("\n[VAULT SYNC] Preparing to push local contributions...")

        result = {"status": "success", "files_staged": [], "message": ""}

        try:
            # Check for new local tools
            local_tools = list(Path("src/tools").glob("*.py"))
            community_tools = await self.storage_backend.list_files("tools")

            new_tools = [t for t in local_tools if t.name not in community_tools and not t.name.startswith("test_")]

            if new_tools:
                print(f"\n[VAULT SYNC] Found {len(new_tools)} new local tools:")
                for tool in new_tools[:5]:  # Show first 5
                    print(f"  • {tool.name}")
                    result["files_staged"].append(f"tools/{tool.name}")

            # Check for new local agents
            local_agents = list(Path("src/agents").glob("*_agent.py"))
            community_agents = await self.storage_backend.list_files("agents")

            new_agents = [a for a in local_agents if a.name not in community_agents]

            if new_agents:
                print(f"\n[VAULT SYNC] Found {len(new_agents)} new local agents:")
                for agent in new_agents[:5]:
                    print(f"  • {agent.name}")
                    result["files_staged"].append(f"agents/{agent.name}")

            # Push new items to storage backend
            if result["files_staged"]:
                for file_path in result["files_staged"]:
                    local_file = Path("src") / file_path
                    success = await self.storage_backend.push(local_file, file_path)
                    if not success:
                        self.logger.error(f"Failed to push {file_path}")

                # Create manifest
                manifest = {
                    "timestamp": datetime.now().isoformat(),
                    "contributor": "anonymous",  # Could be from .env
                    "files": result["files_staged"],
                    "description": "Community contribution from Grokputer",
                }

                manifest_file = self.community_dir / "manifest.json"
                with open(manifest_file, "w") as f:
                    json.dump(manifest, f, indent=2)

                print(f"\n[VAULT SYNC] Pushed {len(result['files_staged'])} items to storage backend")
                result["message"] = f"Successfully pushed {len(result['files_staged'])} items"
            else:
                print("\n[VAULT SYNC] No new items to push")

        except Exception as e:
            self.logger.error(f"Push operation failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def sync_both(self) -> Dict:
        """
        Pull and push in one operation.
        """
        print("\n[VAULT SYNC] Starting bidirectional sync...\n")

        pull_result = await self.pull()
        push_result = await self.push()

        return {"pull": pull_result, "push": push_result}

    def list_community_items(self):
        """
        List available community items.
        """
        print("\n" + "=" * 70)
        print("COMMUNITY VAULT CONTENTS")
        print("=" * 70)

        # List tools
        tools = list((self.community_dir / "tools").glob("*.py"))
        if tools:
            print(f"\n[TOOLS] ({len(tools)}):")
            for tool in sorted(tools)[:10]:
                print(f"  - {tool.name}")

        # List agents
        agents = list((self.community_dir / "agents").glob("*.py"))
        if agents:
            print(f"\n[AGENTS] ({len(agents)}):")
            for agent in sorted(agents)[:10]:
                print(f"  - {agent.name}")

        # List docs
        docs = list((self.community_dir / "docs").glob("*.md"))
        if docs:
            print(f"\n[DOCS] ({len(docs)}):")
            for doc in sorted(docs)[:10]:
                print(f"  - {doc.name}")

        print("\n" + "=" * 70)


async def run_vault_sync_async(action: str = "both", backend_type: str = "local", **backend_kwargs):
    """
    Main entry point for vault sync with async support.

    Args:
        action: 'pull', 'push', or 'both'
        backend_type: 'local', 'git', etc.
        **backend_kwargs: Backend-specific configuration
    """
    # Create appropriate storage backend
    if backend_type == "git":
        backend = GitBackend(
            repo_url=backend_kwargs.get("repo_url", ""),
            local_repo_path=Path(backend_kwargs.get("local_repo_path", "community_repo")),
        )
    else:
        backend = LocalFileBackend(Path("community"))

    sync = VaultSync(storage_backend=backend)

    if action == "pull":
        result = await sync.pull()
    elif action == "push":
        result = await sync.push()
    elif action == "both":
        result = await sync.sync_both()
    elif action == "list":
        sync.list_community_items()
        return
    else:
        print(f"[ERROR] Invalid action: {action}")
        return

    print(f"\n[VAULT SYNC] {action.upper()} complete!\n")
    return result


def run_vault_sync(action: str = "both"):
    """
    Synchronous wrapper for vault sync.

    Args:
        action: 'pull', 'push', or 'both'
    """
    import asyncio

    return asyncio.run(run_vault_sync_async(action))


if __name__ == "__main__":
    # Test vault sync
    import asyncio

    asyncio.run(run_vault_sync_async("pull"))
