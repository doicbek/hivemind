# Hivemind Plugin

Cloud-backed knowledge graph plugin for Claude Code. MCP server + CLI, both thin HTTP clients talking to the Hivemind cloud API.

## Files

```
mcp_server.py        FastMCP server — 18 tools, auto-provisions on startup
cloud_client.py      HTTP client (httpx), auto-registers if no API key
config.py            ~/.hivemind/config.json management (api_key, cloud_url)
cli.py               CLI — auth, store, search, sync, global, migrate, lint
core/
  entity_extractor.py  Regex entity extraction (error-type, library, tool, language, framework, concept)
  sanitizer.py         Privacy censoring for global sync (paths, repo URLs, user IDs)
setup.sh              Installer — deps, MCP registration, skills, CLAUDE.md patch
skills/               /hive, /hive-myelinate, /hive-prune
```

## Key Behaviors

- **Auto-provision**: If no API key in `~/.hivemind/config.json`, the client calls `POST /api/auth/auto-provision` to create an anonymous account
- **Auto-sync**: Every `POST /api/memories` triggers server-side sanitization and GlobalMemory creation
- **Entity extraction**: Regex-based, no LLM calls. Runs on store in cloud_store.py
- **Privacy**: `core/sanitizer.py` strips paths, repo URLs, project names before global sync
