"""
Community Vault Sync for Grokputer
Share and sync tools, agents, and configurations with the community.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class VaultSync:
    """
    Syncs community tools and configurations.
    Uses git for version control and sharing.
    """

    def __init__(self, vault_dir: Path = Path("vault"), community_dir: Path = Path("community")):
        self.vault_dir = vault_dir
        self.community_dir = community_dir
        self.logger = logger

        # Create community directory structure
        self.community_dir.mkdir(exist_ok=True)
        (self.community_dir / "tools").mkdir(exist_ok=True)
        (self.community_dir / "agents").mkdir(exist_ok=True)
        (self.community_dir / "configs").mkdir(exist_ok=True)
        (self.community_dir / "docs").mkdir(exist_ok=True)

    def pull(self) -> Dict:
        """
        Pull latest community contributions.
        """
        print("\n[VAULT SYNC] Pulling latest community contributions...")

        result = {
            "status": "success",
            "tools_updated": [],
            "agents_updated": [],
            "configs_updated": [],
            "new_items": 0
        }

        # For now, copy from docs/ as example community content
        # In production, this would pull from a git repo
        docs_dir = Path("docs")
        if docs_dir.exists():
            # Copy example docs to community
            for doc in docs_dir.glob("*.md"):
                dest = self.community_dir / "docs" / doc.name
                if not dest.exists():
                    try:
                        import shutil
                        shutil.copy2(doc, dest)
                        result["new_items"] += 1
                        print(f"  ✓ New: {doc.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to copy {doc}: {e}")

        # Copy tools from src/tools/
        tools_dir = Path("src/tools")
        if tools_dir.exists():
            for tool in tools_dir.glob("*.py"):
                if tool.name.startswith("test_"):
                    continue
                dest = self.community_dir / "tools" / tool.name
                if not dest.exists():
                    try:
                        import shutil
                        shutil.copy2(tool, dest)
                        result["tools_updated"].append(tool.name)
                        print(f"  ✓ Tool: {tool.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to copy {tool}: {e}")

        # Copy agents from src/agents/
        agents_dir = Path("src/agents")
        if agents_dir.exists():
            for agent in agents_dir.glob("*_agent.py"):
                dest = self.community_dir / "agents" / agent.name
                if not dest.exists():
                    try:
                        import shutil
                        shutil.copy2(agent, dest)
                        result["agents_updated"].append(agent.name)
                        print(f"  ✓ Agent: {agent.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to copy {agent}: {e}")

        print(f"\n[VAULT SYNC] Pull complete!")
        print(f"  New items: {result['new_items']}")
        print(f"  Tools: {len(result['tools_updated'])}")
        print(f"  Agents: {len(result['agents_updated'])}")

        return result

    def push(self) -> Dict:
        """
        Push local contributions to community.
        """
        print("\n[VAULT SYNC] Preparing to push local contributions...")

        result = {
            "status": "success",
            "files_staged": [],
            "message": ""
        }

        # Check for new local tools
        local_tools = list(Path("src/tools").glob("*.py"))
        community_tools = list((self.community_dir / "tools").glob("*.py"))

        new_tools = [
            t for t in local_tools
            if t.name not in [ct.name for ct in community_tools]
            and not t.name.startswith("test_")
        ]

        if new_tools:
            print(f"\n[VAULT SYNC] Found {len(new_tools)} new local tools:")
            for tool in new_tools[:5]:  # Show first 5
                print(f"  • {tool.name}")
                result["files_staged"].append(f"tools/{tool.name}")

        # Check for new local agents
        local_agents = list(Path("src/agents").glob("*_agent.py"))
        community_agents = list((self.community_dir / "agents").glob("*.py"))

        new_agents = [
            a for a in local_agents
            if a.name not in [ca.name for ca in community_agents]
        ]

        if new_agents:
            print(f"\n[VAULT SYNC] Found {len(new_agents)} new local agents:")
            for agent in new_agents[:5]:
                print(f"  • {agent.name}")
                result["files_staged"].append(f"agents/{agent.name}")

        if result["files_staged"]:
            # Create manifest
            manifest = {
                "timestamp": datetime.now().isoformat(),
                "contributor": "anonymous",  # Could be from .env
                "files": result["files_staged"],
                "description": "Community contribution from Grokputer"
            }

            manifest_file = self.community_dir / "manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)

            print(f"\n[VAULT SYNC] Created manifest with {len(result['files_staged'])} items")
            print("[VAULT SYNC] Push staged - use git to complete:")
            print("  git add community/")
            print("  git commit -m 'Community contribution: tools and agents'")
            print("  git push origin main")
        else:
            print("\n[VAULT SYNC] No new items to push")

        return result

    def sync_both(self) -> Dict:
        """
        Pull and push in one operation.
        """
        print("\n[VAULT SYNC] Starting bidirectional sync...\n")

        pull_result = self.pull()
        push_result = self.push()

        return {
            "pull": pull_result,
            "push": push_result
        }

    def list_community_items(self):
        """
        List available community items.
        """
        print("\n" + "="*70)
        print("COMMUNITY VAULT CONTENTS")
        print("="*70)

        # List tools
        tools = list((self.community_dir / "tools").glob("*.py"))
        if tools:
            print(f"\n🔧 TOOLS ({len(tools)}):")
            for tool in sorted(tools)[:10]:
                print(f"  • {tool.name}")

        # List agents
        agents = list((self.community_dir / "agents").glob("*.py"))
        if agents:
            print(f"\n🤖 AGENTS ({len(agents)}):")
            for agent in sorted(agents)[:10]:
                print(f"  • {agent.name}")

        # List docs
        docs = list((self.community_dir / "docs").glob("*.md"))
        if docs:
            print(f"\n📚 DOCS ({len(docs)}):")
            for doc in sorted(docs)[:10]:
                print(f"  • {doc.name}")

        print("\n" + "="*70)


def run_vault_sync(action: str = "both"):
    """
    Main entry point for vault sync.

    Args:
        action: 'pull', 'push', or 'both'
    """
    sync = VaultSync()

    if action == "pull":
        result = sync.pull()
    elif action == "push":
        result = sync.push()
    elif action == "both":
        result = sync.sync_both()
    elif action == "list":
        sync.list_community_items()
        return
    else:
        print(f"[ERROR] Invalid action: {action}")
        return

    print(f"\n[VAULT SYNC] {action.upper()} complete!\n")
    return result


if __name__ == "__main__":
    # Test vault sync
    run_vault_sync("pull")
