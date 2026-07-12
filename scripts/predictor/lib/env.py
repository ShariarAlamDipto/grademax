"""Minimal .env.local loader (no external dependency)."""
from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path

# Repo root = three levels up from this file: lib -> predictor -> scripts -> repo
REPO_ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_env() -> dict[str, str]:
    """Parse .env.local into a dict and also populate os.environ (without overwriting)."""
    env: dict[str, str] = {}
    path = REPO_ROOT / ".env.local"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            env[key] = value
            os.environ.setdefault(key, value)
    return env


def require(key: str) -> str:
    value = load_env().get(key) or os.environ.get(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value
