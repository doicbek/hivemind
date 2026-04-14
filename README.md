<p align="center">
  <img src="hivemindlogo.png" alt="Hivemind logo" width="120">
</p>

<h1 align="center">Hivemind</h1>

<p align="center">
  <strong>A knowledge graph plugin for Claude Code.</strong><br>
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
- **Works Locally or in the Cloud** — Run with a local SQLite database (no account needed) or connect to the cloud for sync and the web dashboard

## Install

```bash
git clone https://github.com/doicbek/hivemind.git ~/hivemind
cd ~/hivemind && bash setup.sh
```

The setup script will:

1. Ask for an API key (optional — press Enter to skip for local-only mode)
2. Install Python dependencies (`httpx`, `mcp`)
3. Register the MCP server globally via `claude mcp add`
4. Install `/hive`, `/hive-myelinate`, `/hive-prune` skills
5. Add memory-augmented guidance to `~/.claude/CLAUDE.md`

### Local vs Cloud Mode

| | Local Mode | Cloud Mode |
|---|---|---|
| **Setup** | No account needed | API key from [web dashboard](https://hivemind-nine.vercel.app) |
| **Storage** | SQLite at `~/.hivemind/hivemind.db` | Cloud Neo4j |
| **Search** | FTS5 full-text search | Full-text + graph expansion |
| **Web dashboard** | Not available | Personal graph visualization |
| **Global graph** | Not available | Community knowledge sharing |
| **Upgrade** | `python3 cli.py claim YOUR_KEY` | Already connected |

Start local, connect to the cloud when you're ready:

```bash
python3 ~/hivemind/cli.py claim YOUR_API_KEY
```

This uploads all your local memories to the cloud and switches to cloud mode. Your local database is preserved as a backup.

## How It Works

```
Claude Code Session
    |
    v
MCP Server (18 tools)
    |
    |--- Local mode ---> SQLite (FTS5 search, entity extraction)
    |--- Cloud mode ---> Cloud API ---> Neo4j + auto-sync to Global Graph
    |
    v
Smarter sessions, fewer re-discoveries
```

### The Loop

1. **Before starting work**, Claude checks Hivemind for relevant past patterns (`get_memories_for_task`)
2. **During the session**, Claude can search for specific errors or techniques (`search_memories`, `search_with_expansion`)
3. **After the session**, run `/hive` to extract and store valuable patterns
4. **Over time**, run `/hive-myelinate` to synthesize knowledge into wiki pages
5. **In cloud mode**, every stored memory is automatically synced to the global knowledge graph (privacy-sanitized)

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
| `store_memory` | Store a problem-solving pattern |
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
| `sync_to_global` | Manual sync to global graph (cloud mode) |
| `search_global` | Search the community knowledge graph (cloud mode) |
| `browse_global` | Browse global categories (cloud mode) |

## Skills

| Skill | Description |
|-------|-------------|
| `/hive` | Extract problem-solving patterns from the current session transcript and store as memories |
| `/hive-myelinate` | Find knowledge gaps across your graph and create synthesis wiki pages |
| `/hive-prune` | Run graph health checks — fix orphaned memories, stale syntheses, and duplicates |

## Privacy

When memories sync to the global knowledge graph (cloud mode), a client-side sanitizer automatically:

- Replaces file paths (`/home/user/repos/acme/src/auth.py` -> `[path]/auth.py`)
- Replaces repository URLs (`github.com/org/repo` -> `[private-repo]`)
- Replaces project identifiers with `[private]`
- Strips user IDs and session IDs

Your code stays private. Only the problem-solving *patterns* are shared.

Preview what sanitization looks like:

```bash
python3 ~/hivemind/cli.py sync --dry-run
```

## Web Dashboard

Create an account on the [Hivemind web dashboard](https://hivemind-nine.vercel.app) to access:

- **Personal Graph** — Force-directed visualization of your knowledge graph
- **Global Graph** — Browse the community's anonymized knowledge
- **Search** — Full-text search with graph expansion highlighting
- **API Keys** — Create API keys to connect the CLI plugin

## CLI Reference

The CLI is available for power users but never required:

```bash
python3 ~/hivemind/cli.py search "import error"          # Full-text search
python3 ~/hivemind/cli.py search-expanded "import error"  # Search + expansion
python3 ~/hivemind/cli.py categories                      # List category tree
python3 ~/hivemind/cli.py claim YOUR_API_KEY              # Connect local DB to cloud
python3 ~/hivemind/cli.py global search "query"           # Search global graph
python3 ~/hivemind/cli.py global stats                    # Global statistics
python3 ~/hivemind/cli.py auth status                     # Check connection
python3 ~/hivemind/cli.py lint                            # Graph health check
```

## Architecture

```
User's Machine                          Cloud (optional)
─────────────                          ────────────────

Claude Code                            Hivemind Cloud
    |                                  ├── FastAPI backend
    v                                  ├── Neo4j knowledge graph
MCP Server (18 tools)                  ├── User-scoped data
    |                                  ├── Global graph (sanitized)
    v                                  └── Web dashboard
local_client.py (SQLite)
    -- or --
cloud_client.py ──── HTTPS ──────────>
```

In local mode, everything runs on your machine with SQLite. In cloud mode, data syncs to Neo4j with the web dashboard and global graph.

## License

MIT
