"""Local configuration management for Hivemind.

Stores API key and cloud URL in ~/.hivemind/config.json.
"""

import json
import os

CONFIG_DIR = os.path.expanduser("~/.hivemind")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CLOUD_URL = "https://hivemind.example.com"


def _ensure_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load() -> dict:
    """Load config from disk. Returns empty dict if no config exists."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save(config: dict):
    """Write config to disk."""
    _ensure_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def get_api_key() -> str | None:
    """Return stored API key, or None."""
    return load().get("api_key")


def set_api_key(key: str):
    """Store an API key."""
    cfg = load()
    cfg["api_key"] = key
    save(cfg)


def clear_api_key():
    """Remove stored API key."""
    cfg = load()
    cfg.pop("api_key", None)
    save(cfg)


def get_cloud_url() -> str:
    """Return cloud base URL."""
    return load().get("cloud_url", DEFAULT_CLOUD_URL)


def set_cloud_url(url: str):
    """Override cloud base URL."""
    cfg = load()
    cfg["cloud_url"] = url.rstrip("/")
    save(cfg)
