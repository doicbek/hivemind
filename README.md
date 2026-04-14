<p align="center">
  <img src="hivemindlogo.png" alt="Hivemind logo" width="120">
</p>

<h1 align="center">Hivemind</h1>

<p align="center">
  <strong>A cloud-backed knowledge graph plugin for Claude Code.</strong><br>
  Capture problem-solving patterns. Search past solutions. Share knowledge globally.
</p>

<p align="center">
  <a href="#install">Install</a> &bull;
  <a href="#how-it-works">How It Works</a> &bull;
  <a href="#mcp-tools">MCP Tools</a> &bull;
  <a href="#skills">Skills</a> &bull;
  <a href="#privacy">Privacy</a> &bull;
  <a href="#web-dashboard">Web Dashboard</a>
</p>

---

## Why Hivemind?

Every Claude Code session generates valuable problem-solving knowledge — debugging strategies, error recovery workflows, architectural decisions, tool usage patterns. Without Hivemind, that knowledge evaporates when the session ends.

Hivemind **captures, indexes, and resurfaces** that knowledge automatically:

- **Knowledge Graph** — Memories are linked through extracted entities (libraries, error types, frameworks, concepts) forming a searchable graph, not just a flat list
- **Graph-Powered Search** — Find related memories through shared entities, even when keywords don't match
- **Synthesis Pages** — Aggregate knowledge across memories into living wiki pages that compound over time
- **Global Knowledge Graph** — Anonymized, community-shared patterns. Learn from how others solved similar problems
- **Zero Setup** — Auto-provisions on first use. No registration, no API keys, no CLI commands

## Install

```bash
git clone https://github.com/doicbek/hivemind.git ~/.hivemind/repo
bash ~/.hivemind/repo/setup.sh
```

Done. Start a new Claude Code session and Hivemind is active. The setup script:

1. Installs Python dependencies (`httpx`, `mcp`)
2. Registers the MCP server globally via `claude mcp add`
3. Installs `/hive`, `/hive-myelinate`, `/hive-prune` skills
4. Adds memory-augmented guidance to `~/.claude/CLAUDE.md`

Your account is auto-provisioned on first use — no registration required.

## How It Works

```
Claude Code Session
    |
    v
MCP Server (18 tools)                    Cloud
    |                                      |
    |--- search_memories -----> cloud API ---> Neo4j
    |--- store_memory --------> cloud API ---> Neo4j + auto-sync to Global Graph
    |--- get_memories_for_task -> cloud API ---> Full-text + entity graph expansion
    |
    v
Smarter sessions, fewer re-discoveries
```

### The Loop

1. **Before starting work**, Claude checks Hivemind for relevant past patterns (`get_memories_for_task`)
2. **During the session**, Claude can search for specific errors or techniques (`search_memories`, `search_with_expansion`)
3. **After the session**, run `/hive` to extract and store valuable patterns
4. **Over time**, run `/hive-myelinate` to synthesize knowledge into wiki pages
5. **Every stored memory** is automatically synced to the global knowledge graph (privacy-sanitized)

### Entity Extraction

Entities are automatically extracted using fast regex matching — no LLM calls, no latency:

| Entity Type | Examples |
|---|---|
| `error-type` | ImportError, ConnectionRefusedError, SIGKILL |
| `library` | neo4j, requests, numpy, boto3 |
| `tool` | Grep, Bash, Edit, Agent |
| `language` | Python, TypeScript, Rust, Go |
| `framework` | FastAPI, React, pytest, Django |
| `concept` | circular-import, lazy-loading, race-condition |

These entities power **graph-based search expansion** — when you search for "connection timeout", Hivemind finds direct matches *and* memories linked through shared entities like `neo4j`, `retry-logic`, or `ConnectionError`.

## MCP Tools

Available in every Claude Code session:

| Tool | Description |
|------|-------------|
| `store_memory` | Store a problem-solving pattern (auto-syncs to global) |
| `search_memories` | Full-text search across all your memories |
| `search_with_expansion` | Search + graph-based entity expansion |
| `get_memories_for_task` | Find memories relevant to a task (returns full workflows) |
| `browse_categories` | Browse the category tree |
| `get_memory` | Full memory details by ID |
| `search_by_category` | Browse memories in a category |
| `synthesize_topic` | Create a synthesis wiki page |
| `update_synthesis_node` | Update an existing synthesis |
| `list_syntheses` | List all synthesis pages |
| `get_synthesis_detail` | Full synthesis details |
| `find_synthesis_gaps` | Find topics needing synthesis |
| `promote_query` | Promote a search result to a synthesis |
| `lint_graph` | Run graph health checks |
| `view_log` | Browse activity log |
| `sync_to_global` | Manual sync to global graph |
| `search_global` | Search the community knowledge graph |
| `browse_global` | Browse global categories |

## Skills

| Skill | Description |
|-------|-------------|
| `/hive` | Extract problem-solving patterns from the current session transcript and store as memories |
| `/hive-myelinate` | Find knowledge gaps across your graph and create synthesis wiki pages |
| `/hive-prune` | Run graph health checks — fix orphaned memories, stale syntheses, and duplicates |

## Privacy

When memories sync to the global knowledge graph, a client-side sanitizer automatically:

- Replaces file paths (`/home/user/repos/acme/src/auth.py` -> `[path]/auth.py`)
- Replaces repository URLs (`github.com/org/repo` -> `[private-repo]`)
- Replaces project identifiers with `[private]`
- Strips user IDs and session IDs

Your code stays private. Only the problem-solving *patterns* are shared.

Preview what sanitization looks like:

```bash
python3 ~/.hivemind/repo/cli.py sync --dry-run
```

## Web Dashboard

Claim your auto-provisioned account on the [Hivemind web dashboard](https://hivemind-nine.vercel.app) to access:

- **Personal Graph** — Force-directed visualization of your knowledge graph
- **Global Graph** — Browse the community's anonymized knowledge
- **Search** — Full-text search with graph expansion highlighting
- **API Keys** — Manage API keys for multiple machines

Claiming is optional — the plugin works fully without it.

## CLI Reference

The CLI is available for power users but never required:

```bash
python3 ~/.hivemind/repo/cli.py search "import error"          # Full-text search
python3 ~/.hivemind/repo/cli.py search-expanded "import error"  # Search + expansion
python3 ~/.hivemind/repo/cli.py categories                      # List category tree
python3 ~/.hivemind/repo/cli.py global search "query"           # Search global graph
python3 ~/.hivemind/repo/cli.py global stats                    # Global statistics
python3 ~/.hivemind/repo/cli.py auth status                     # Check connection
python3 ~/.hivemind/repo/cli.py lint                            # Graph health check
```

## Architecture

```
User's Machine                          Cloud
─────────────                          ─────

Claude Code                            Hivemind Cloud
    │                                  ├── FastAPI backend
    v                                  ├── Neo4j knowledge graph
MCP Server (18 tools)                  ├── User-scoped data
    │                                  ├── Global graph (sanitized)
    v                                  └── Web dashboard
cloud_client.py ──── HTTPS ──────────>
    (auto-provisioned API key)
```

No local database. No manual configuration. All data lives in the cloud, scoped by user.

## License

MIT
