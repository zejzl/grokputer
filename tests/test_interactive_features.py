"""
Tests for interactive mode features (modes 4-6).
"""

import pytest
import tempfile
import json
from pathlib import Path


class TestSessionImprover:
    """Tests for session improvement (mode 4)."""

    def test_session_improver_initialization(self):
        """Test SessionImprover can be initialized."""
        from src.agents.session_improver import SessionImprover

        with tempfile.TemporaryDirectory() as tmpdir:
            improver = SessionImprover(logs_dir=Path(tmpdir))
            assert improver is not None
            assert improver.logs_dir == Path(tmpdir)

    def test_get_latest_session_no_sessions(self):
        """Test get_latest_session returns None when no sessions exist."""
        from src.agents.session_improver import SessionImprover

        with tempfile.TemporaryDirectory() as tmpdir:
            improver = SessionImprover(logs_dir=Path(tmpdir))
            result = improver.get_latest_session()
            assert result is None

    def test_get_latest_session_with_sessions(self):
        """Test get_latest_session returns most recent session."""
        from src.agents.session_improver import SessionImprover

        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir)

            # Create test sessions
            session1 = logs_dir / "session_001"
            session1.mkdir()
            (session1 / "session.json").write_text('{"task": "test1"}')

            session2 = logs_dir / "session_002"
            session2.mkdir()
            (session2 / "session.json").write_text('{"task": "test2"}')

            improver = SessionImprover(logs_dir=logs_dir)
            latest = improver.get_latest_session()

            assert latest in ["session_001", "session_002"]

    def test_analyze_nonexistent_session(self):
        """Test analyzing a session that doesn't exist."""
        from src.agents.session_improver import SessionImprover

        with tempfile.TemporaryDirectory() as tmpdir:
            improver = SessionImprover(logs_dir=Path(tmpdir))
            result = improver.analyze_session("nonexistent")

            assert "error" in result


class TestOfflineMode:
    """Tests for offline mode (mode 5)."""

    def test_offline_cache_initialization(self):
        """Test OfflineCache can be initialized."""
        from src.offline_mode import OfflineCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = OfflineCache(cache_dir=Path(tmpdir))
            assert cache is not None
            assert cache.cache_dir.exists()

    def test_offline_cache_knowledge_base(self):
        """Test knowledge base is created."""
        from src.offline_mode import OfflineCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = OfflineCache(cache_dir=Path(tmpdir))
            assert isinstance(cache.knowledge_base, dict)
            assert "common_tasks" in cache.knowledge_base

    def test_find_similar_task_no_match(self):
        """Test finding similar task when none exists."""
        from src.offline_mode import OfflineCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = OfflineCache(cache_dir=Path(tmpdir))
            result = cache.find_similar_task("completely unique task")
            assert result is None

    def test_generate_offline_response(self):
        """Test generating offline response."""
        from src.offline_mode import OfflineCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = OfflineCache(cache_dir=Path(tmpdir))
            response = cache.generate_offline_response("test task")

            assert response["status"] == "offline"
            assert "content" in response
            assert isinstance(response["tool_calls"], list)


class TestVaultSync:
    """Tests for vault sync (mode 6)."""

    def test_vault_sync_initialization(self):
        """Test VaultSync can be initialized."""
        from src.vault_sync import VaultSync

        with tempfile.TemporaryDirectory() as tmpdir:
            sync = VaultSync(
                vault_dir=Path(tmpdir) / "vault",
                community_dir=Path(tmpdir) / "community"
            )
            assert sync is not None
            assert sync.community_dir.exists()

    def test_vault_sync_directory_structure(self):
        """Test vault sync creates proper directory structure."""
        from src.vault_sync import VaultSync

        with tempfile.TemporaryDirectory() as tmpdir:
            sync = VaultSync(community_dir=Path(tmpdir) / "community")

            assert (sync.community_dir / "tools").exists()
            assert (sync.community_dir / "agents").exists()
            assert (sync.community_dir / "configs").exists()
            assert (sync.community_dir / "docs").exists()

    def test_pull_operation(self):
        """Test pull operation completes."""
        from src.vault_sync import VaultSync

        with tempfile.TemporaryDirectory() as tmpdir:
            sync = VaultSync(community_dir=Path(tmpdir) / "community")
            result = sync.pull()

            assert result["status"] == "success"
            assert isinstance(result["tools_updated"], list)
            assert isinstance(result["agents_updated"], list)

    def test_push_operation(self):
        """Test push operation completes."""
        from src.vault_sync import VaultSync

        with tempfile.TemporaryDirectory() as tmpdir:
            sync = VaultSync(community_dir=Path(tmpdir) / "community")
            result = sync.push()

            assert result["status"] == "success"
            assert isinstance(result["files_staged"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
