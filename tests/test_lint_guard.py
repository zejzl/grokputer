"""Guard: src/ has no flake8 errors (syntax errors, undefined names)."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Same selection as `automate.sh quality`
SELECT = "E9,F63,F7,F82,F824"


@pytest.mark.skipif(importlib.util.find_spec("flake8") is None, reason="flake8 not installed")
def test_src_has_no_undefined_names():
    result = subprocess.run(
        [sys.executable, "-m", "flake8", "src", f"--select={SELECT}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout
