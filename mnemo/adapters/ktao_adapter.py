"""Ktao adapter through memory.py CLI.

Compatible with both:
- Upstream Ktao repo layout (``src/memory.py``)
- Local fork layout used in this workspace (``skills/memory-system/scripts/memory.py``)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class KtaoAdapter:
    """Adapter calling memory.py CLI commands."""

    def __init__(self, workspace: Path) -> None:
        """Initialize adapter with workspace root."""

        self.workspace = workspace
        self.memory_py = self._resolve_memory_py()

    def _resolve_memory_py(self) -> Path:
        """Resolve memory.py path across different Ktao layouts."""

        # Optional explicit override.
        override = os.getenv("MNEMO_KTAO_MEMORY_PY")
        if override:
            p = Path(override).expanduser().resolve()
            if p.exists():
                return p

        candidates = [
            self.workspace / "memory.py",  # legacy single-file layout
            self.workspace / "src" / "memory.py",  # upstream layout
            self.workspace / "scripts" / "memory.py",  # possible packaged layout
            self.workspace / "skills" / "memory-system" / "scripts" / "memory.py",  # local fork
        ]
        for p in candidates:
            if p.exists():
                return p

        searched = "\n  - ".join(str(p) for p in candidates)
        raise FileNotFoundError(
            "Cannot find Ktao memory.py. Set MNEMO_KTAO_MEMORY_PY or place file in one of:\n"
            f"  - {searched}"
        )

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run memory.py command and return process result."""

        cmd = [sys.executable, str(self.memory_py), *args]
        return subprocess.run(
            cmd,
            cwd=self.memory_py.parent,
            capture_output=True,
            text=True,
            check=False,
        )
