#!/usr/bin/env python3
"""Register the corpus-inference-query MCP server with Claude Desktop (and optionally Claude Code).

This script:
1. Installs the package via `uv tool install` if the binary is not in PATH or a local venv.
2. Adds/updates the MCP server entry in the Claude Desktop config (macOS/Linux).
3. Optionally updates Claude Code settings (`~/.claude/settings.json`).

Usage:
    python scripts/register_mcp.py [--claude-code]
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_BINARY_NAME = "corpus-inference-query"
_CLAUDE_CODE_SETTINGS = Path.home() / ".claude" / "settings.json"


def _claude_desktop_config() -> Path:
    """Return the platform-specific Claude Desktop config path."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _find_binary(repo_root: Path) -> str | None:
    """Return the absolute path to the corpus-inference-query binary, or None.

    Checks PATH first (uv tool install / pipx), then the repo-local venv.
    """
    found = shutil.which(_BINARY_NAME)
    if found:
        return str(Path(found).resolve())
    for candidate in (
        repo_root / ".venv" / "bin" / _BINARY_NAME,
        repo_root / ".venv" / "Scripts" / f"{_BINARY_NAME}.exe",
    ):
        if candidate.exists():
            return str(candidate.resolve())
    return None


def _install_via_uv(repo_root: Path) -> str:
    """Install the package with `uv tool install` and return the binary path."""
    if shutil.which("uv") is None:
        raise RuntimeError(
            "uv is not installed. Install it first "
            "(https://docs.astral.sh/uv/getting-started/installation/) "
            "or run scripts/install_local.sh to create a local venv."
        )
    subprocess.run(
        ["uv", "tool", "install", str(repo_root)],
        check=True,
    )
    binary = _find_binary(repo_root)
    if binary is None:
        raise RuntimeError(
            "Installation succeeded but corpus-inference-query was not found in PATH. "
            "Ensure ~/.local/bin (or the uv tool bin dir) is on your PATH."
        )
    return binary


def _load_json(path: Path) -> dict:
    """Load a JSON file, returning an empty dict if it does not exist."""
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _save_json(path: Path, data: dict) -> None:
    """Save a dict to a JSON file with pretty formatting."""
    path.write_text(json.dumps(data, indent=2) + "\n")


def _register(config_path: Path, app_name: str, binary_path: str, corpus_path: str | None) -> bool:
    """Add the MCP server entry to a Claude config file. Returns True on success."""
    if not config_path.parent.is_dir():
        print(
            f"Skipping {app_name}: {config_path.parent} does not exist.\n"
            f"  Install {app_name} first (which creates that directory), or create it\n"
            f"  manually with: mkdir -p \"{config_path.parent}\"",
            file=sys.stderr,
        )
        return False

    config = _load_json(config_path)
    mcp_servers = config.setdefault("mcpServers", {})

    entry: dict = {
        "type": "stdio",
        "command": binary_path,
    }
    if corpus_path:
        entry["env"] = {"CORPUS_INFERENCE_PATH": corpus_path}

    mcp_servers[_BINARY_NAME] = entry
    _save_json(config_path, config)
    print(f"Registered {_BINARY_NAME} in {config_path}")
    return True


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    corpus_path = os.environ.get("CORPUS_INFERENCE_PATH")
    register_claude_code = "--claude-code" in sys.argv

    binary = _find_binary(repo_root)
    if binary is None:
        print("corpus-inference-query not found in PATH or local venv. Installing via uv tool install ...")
        binary = _install_via_uv(repo_root)
        print(f"Installed at {binary}")
    else:
        print(f"Found corpus-inference-query at {binary}")

    registered = _register(_claude_desktop_config(), "Claude Desktop", binary, corpus_path)

    if register_claude_code:
        registered = _register(_CLAUDE_CODE_SETTINGS, "Claude Code", binary, corpus_path) or registered

    if not registered:
        print("\nNo config file was updated.", file=sys.stderr)
        return 1

    print("\nDone. Restart Claude Desktop (and Claude Code if applicable) to load the MCP server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
