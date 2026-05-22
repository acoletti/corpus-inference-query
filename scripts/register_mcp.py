#!/usr/bin/env python3
"""Register the code-inference-query MCP server with Claude Desktop (and optionally Claude Code).

This script:
1. Installs the package via `uv tool install` if the binary is not in PATH.
2. Adds/updates the MCP server entry in the Claude Desktop config.
3. Optionally updates Claude Code settings (`~/.claude/settings.json`).

Usage:
    python scripts/register_mcp.py [--claude-code]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


_CLAUDE_DESKTOP_CONFIG = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
_CLAUDE_CODE_SETTINGS = Path.home() / ".claude/settings.json"


def _find_binary() -> str | None:
    """Return the absolute path to the code-inference-query binary, or None."""
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(path_dir) / "code-inference-query"
        if candidate.exists():
            return str(candidate.resolve())
    return None


def _install_via_uv(repo_root: Path) -> str:
    """Install the package with `uv tool install` and return the binary path."""
    subprocess.run(
        ["uv", "tool", "install", str(repo_root)],
        check=True,
    )
    binary = _find_binary()
    if binary is None:
        raise RuntimeError(
            "Installation succeeded but code-inference-query was not found in PATH. "
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _register_claude_desktop(binary_path: str, corpus_path: str | None = None) -> None:
    """Add the MCP server entry to the Claude Desktop config."""
    config = _load_json(_CLAUDE_DESKTOP_CONFIG)
    mcp_servers = config.setdefault("mcpServers", {})

    entry: dict = {
        "type": "stdio",
        "command": binary_path,
    }
    if corpus_path:
        entry["env"] = {"CODE_INFERENCE_CORPUS_PATH": corpus_path}

    mcp_servers["code-inference-query"] = entry
    _save_json(_CLAUDE_DESKTOP_CONFIG, config)
    print(f"Registered code-inference-query in {_CLAUDE_DESKTOP_CONFIG}")


def _register_claude_code(binary_path: str, corpus_path: str | None = None) -> None:
    """Add the MCP server entry to the Claude Code settings."""
    config = _load_json(_CLAUDE_CODE_SETTINGS)
    mcp_servers = config.setdefault("mcpServers", {})

    entry: dict = {
        "type": "stdio",
        "command": binary_path,
    }
    if corpus_path:
        entry["env"] = {"CODE_INFERENCE_CORPUS_PATH": corpus_path}

    mcp_servers["code-inference-query"] = entry
    _save_json(_CLAUDE_CODE_SETTINGS, config)
    print(f"Registered code-inference-query in {_CLAUDE_CODE_SETTINGS}")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    corpus_path = os.environ.get("CODE_INFERENCE_CORPUS_PATH")
    register_claude_code = "--claude-code" in sys.argv

    binary = _find_binary()
    if binary is None:
        print("code-inference-query not found in PATH. Installing via uv tool install ...")
        binary = _install_via_uv(repo_root)
        print(f"Installed at {binary}")
    else:
        print(f"Found code-inference-query at {binary}")

    _register_claude_desktop(binary, corpus_path)

    if register_claude_code:
        _register_claude_code(binary, corpus_path)

    print("\nDone. Restart Claude Desktop (and Claude Code if applicable) to load the MCP server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
