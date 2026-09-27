"""Short git revision for sealed rows. Unknown is allowed when git is not there."""

from __future__ import annotations

import subprocess

from config import BACKEND_DIR


def get_git_sha() -> str:
    try:
        repo_root = BACKEND_DIR.parent
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return "unknown"
