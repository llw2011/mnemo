"""Ktao adapter through memory.py CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path


class KtaoAdapter:
    """Adapter calling memory.py CLI commands."""

    def __init__(self, workspace: Path) -> None:
        """Initialize adapter with workspace root."""

        self.workspace = workspace

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run memory.py command and return process result."""

        cmd = ["python", str(self.workspace / "memory.py"), *args]
        return subprocess.run(cmd, cwd=self.workspace, capture_output=True, text=True, check=False)
