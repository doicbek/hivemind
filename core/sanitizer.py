"""Privacy sanitizer for Hivemind global sync.

Censors private repository names, file paths, and user identifiers
before memories are pushed to the global knowledge graph.
"""

import re
from pathlib import PurePosixPath

# Unix absolute paths with 3+ segments
_UNIX_PATH = re.compile(r"(/[\w._-]+){3,}(\.\w+)?")
# Home-relative paths
_HOME_PATH = re.compile(r"~/[\w/._-]+")
# Windows paths
_WIN_PATH = re.compile(r"[A-Z]:\\[\w\\._-]+")
# Git hosting URLs (github, gitlab, bitbucket)
_REPO_URL = re.compile(
    r"(?:https?://)?(?:github|gitlab|bitbucket)\.com/[\w.-]+/[\w.-]+", re.IGNORECASE
)
# git@host:org/repo patterns
_GIT_SSH = re.compile(r"git@[\w.-]+:[\w.-]+/[\w.-]+")


def _replace_path(match: re.Match) -> str:
    """Keep only the filename from a matched path."""
    path = match.group(0)
    name = PurePosixPath(path.replace("\\", "/")).name
    if name:
        return f"[path]/{name}"
    return "[path]"


def sanitize_text(text: str) -> str:
    """Remove private paths and repo references from a string."""
    if not text:
        return text

    # Order matters: longest/most-specific patterns first
    text = _REPO_URL.sub("[private-repo]", text)
    text = _GIT_SSH.sub("[private-repo]", text)
    text = _HOME_PATH.sub(lambda m: _replace_path(m), text)
    text = _UNIX_PATH.sub(lambda m: _replace_path(m), text)
    text = _WIN_PATH.sub(lambda m: _replace_path(m), text)

    return text


def sanitize_memory(memory: dict) -> dict:
    """Return a sanitized copy of a memory dict, safe for global sharing.

    Censors:
    - File paths → [path]/filename
    - Repo URLs → [private-repo]
    - project field → [private]
    - user_id, session_id → stripped
    """
    sanitized = memory.copy()

    # Censor text fields
    for field in ("title", "summary", "workflow"):
        if sanitized.get(field):
            sanitized[field] = sanitize_text(sanitized[field])

    # Replace project with opaque marker
    sanitized["project"] = "[private]"

    # Strip identifying fields (contributor tracked via API key server-side)
    sanitized.pop("user_id", None)
    sanitized.pop("session_id", None)

    return sanitized


def preview_diff(memory: dict) -> dict:
    """Show what sanitization would change. Returns dict of field → (before, after)."""
    sanitized = sanitize_memory(memory)
    diff = {}
    for field in ("title", "summary", "workflow", "project"):
        before = memory.get(field, "")
        after = sanitized.get(field, "")
        if before != after:
            diff[field] = {"before": before, "after": after}

    for field in ("user_id", "session_id"):
        if memory.get(field):
            diff[field] = {"before": memory[field], "after": "[removed]"}

    return diff
