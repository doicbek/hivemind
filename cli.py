#!/usr/bin/env python3
"""CLI interface for Hivemind session memory system.

Cloud-first: all operations go through the cloud API via cloud_client.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import cloud_client
from core.sanitizer import sanitize_memory, preview_diff


def _get_client():
    return cloud_client.get_client()


def _print_json(data):
    print(json.dumps(data, indent=2, default=str))


# ── Auth Commands ────────────────────────────────────────────────────

def cmd_auth_set_key(args):
    """Store an API key locally."""
    config.set_api_key(args.key)
    print(json.dumps({"stored": True, "message": "API key saved to ~/.hivemind/config.json"}))


def cmd_auth_status(args):
    """Check authentication status."""
    key = config.get_api_key()
    if not key:
        print(json.dumps({"authenticated": False, "message": "No API key configured"}))
        return

    try:
        client = _get_client()
        result = client.auth_status()
        _print_json(result)
    except Exception as e:
        print(json.dumps({"authenticated": False, "error": str(e)}), file=sys.stderr)


def cmd_auth_clear_key(args):
    """Remove stored API key."""
    config.clear_api_key()
    print(json.dumps({"cleared": True}))


# ── Memory Commands ──────────────────────────────────────────────────

def cmd_store(args):
    """Store a memory from JSON input."""
    data = json.loads(args.json)
    required = ["title", "summary", "workflow", "tools_used", "categories", "project", "session_id"]
    missing = [k for k in required if k not in data]
    if missing:
        print(json.dumps({"error": f"Missing fields: {missing}"}), file=sys.stderr)
        sys.exit(1)

    client = _get_client()
    memory_id = client.store_memory(
        title=data["title"],
        summary=data["summary"],
        workflow=data["workflow"],
        tools_used=data["tools_used"],
        categories=data["categories"],
        project=data["project"],
        session_id=data["session_id"],
    )
    print(json.dumps({"stored": True, "id": memory_id}))


def cmd_search(args):
    """Search memories by text query."""
    client = _get_client()
    results = client.search_memories(args.query, limit=args.limit)
    _print_json({"results": results})


def cmd_search_category(args):
    """Search memories by category."""
    client = _get_client()
    results = client.search_by_category(args.category, limit=args.limit)
    _print_json({"results": results})


def cmd_get(args):
    """Get full memory details."""
    client = _get_client()
    result = client.get_memory(args.id)
    if result is None:
        print(json.dumps({"error": "Memory not found"}), file=sys.stderr)
        sys.exit(1)
    _print_json({"memory": result})


def cmd_search_expanded(args):
    """Search memories with graph-based expansion."""
    client = _get_client()
    results = client.search_with_expansion(
        args.query, limit=args.limit, expansion_limit=args.expansion_limit,
    )
    _print_json(results)


def cmd_categories(args):
    """List existing category tree."""
    client = _get_client()
    cats = client.get_categories()
    _print_json({"categories": cats})


def cmd_backfill_entities(args):
    """Backfill entity extraction for existing memories."""
    client = _get_client()
    result = client.backfill_entities()
    _print_json(result)


def cmd_log(args):
    """Display activity log."""
    client = _get_client()
    entries = client.get_log(limit=args.limit, action_filter=args.action or None)
    _print_json({"entries": entries})


# ── Synthesis Commands ───────────────────────────────────────────────

def cmd_synthesize(args):
    """Create a synthesis node from JSON input."""
    data = json.loads(args.json)
    required = ["topic", "summary", "key_findings", "memory_ids"]
    missing = [k for k in required if k not in data]
    if missing:
        print(json.dumps({"error": f"Missing fields: {missing}"}), file=sys.stderr)
        sys.exit(1)

    client = _get_client()
    sid = client.create_synthesis(
        topic=data["topic"],
        summary=data["summary"],
        key_findings=data["key_findings"],
        memory_ids=data["memory_ids"],
        entity_keys=data.get("entity_keys"),
    )
    print(json.dumps({"stored": True, "id": sid}))


def cmd_list_syntheses(args):
    """List synthesis nodes."""
    client = _get_client()
    results = client.list_syntheses(limit=args.limit)
    _print_json({"syntheses": results})


def cmd_get_synthesis(args):
    """Get full synthesis details."""
    client = _get_client()
    result = client.get_synthesis(args.id)
    if result is None:
        print(json.dumps({"error": "Synthesis not found"}), file=sys.stderr)
        sys.exit(1)
    _print_json({"synthesis": result})


def cmd_find_synthesis_gaps(args):
    """Find entity clusters lacking synthesis."""
    client = _get_client()
    gaps = client.find_synthesis_gaps(min_memories=args.min_memories)
    _print_json({"gaps": gaps, "count": len(gaps)})


# ── Lint ─────────────────────────────────────────────────────────────

def cmd_lint(args):
    """Run graph health check."""
    client = _get_client()
    report = client.lint()
    _print_json(report)


# ── Transcript ───────────────────────────────────────────────────────

def cmd_transcript(args):
    """Read and return session transcript (local operation)."""
    project_dir = args.project_path.replace("/", "-").strip("-")
    transcript_dir = os.path.expanduser(f"~/.claude/projects/{project_dir}")

    transcript_file = os.path.join(transcript_dir, f"{args.session_id}.jsonl")

    if not os.path.exists(transcript_file):
        if os.path.isdir(transcript_dir):
            files = [f for f in os.listdir(transcript_dir) if f.endswith(".jsonl")]
            if files:
                files.sort(key=lambda f: os.path.getmtime(os.path.join(transcript_dir, f)), reverse=True)
                transcript_file = os.path.join(transcript_dir, files[0])
            else:
                print(json.dumps({"error": f"No transcripts found in {transcript_dir}"}), file=sys.stderr)
                sys.exit(1)
        else:
            print(json.dumps({"error": f"Directory not found: {transcript_dir}"}), file=sys.stderr)
            sys.exit(1)

    entries = []
    with open(transcript_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    _print_json({
        "file": transcript_file,
        "entry_count": len(entries),
        "entries": entries,
    })


# ── Migrate Command ──────────────────────────────────────────────────

def cmd_migrate(args):
    """Migrate existing local Neo4j memories to the cloud.

    Reads all memories from local Neo4j (using HIVE_NEO4J_* env vars),
    then uploads them to the cloud API under the authenticated user.
    """
    # Import local memory_store for reading from local Neo4j
    try:
        from memory_store import get_driver as get_local_driver
    except ImportError:
        # Try the original file directly
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "local_memory_store",
            os.path.join(os.path.dirname(__file__), "memory_store_local.py"),
        )
        if spec is None:
            print(json.dumps({"error": "Cannot find local memory_store. Is Neo4j configured?"}), file=sys.stderr)
            sys.exit(1)
        mod = importlib.util.load_module(spec)
        get_local_driver = mod.get_driver

    from neo4j import GraphDatabase

    neo4j_uri = os.environ.get("HIVE_NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("HIVE_NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("HIVE_NEO4J_PASSWORD", "password")

    print(f"Connecting to local Neo4j at {neo4j_uri}...", file=sys.stderr)
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    # Read all memories from local
    with driver.session() as session:
        result = session.run(
            "MATCH (m:Memory) "
            "OPTIONAL MATCH (m)-[:BELONGS_TO]->(c:Category) "
            "OPTIONAL MATCH (m)-[:USES_TOOL]->(t:Tool) "
            "RETURN m.id AS id, m.title AS title, m.summary AS summary, "
            "m.workflow AS workflow, m.tools_used AS tools_used, "
            "m.session_id AS session_id, m.project AS project, "
            "m.user_id AS user_id, m.created_at AS created_at, "
            "collect(DISTINCT c.name) AS categories, "
            "collect(DISTINCT t.name) AS tools "
            "ORDER BY m.created_at"
        )
        memories = []
        for r in result:
            mem = dict(r)
            # Serialize datetime
            for k, v in mem.items():
                if hasattr(v, "isoformat"):
                    mem[k] = v.isoformat()
            memories.append(mem)

    # Also read syntheses
    with driver.session() as session:
        result = session.run(
            "MATCH (s:Synthesis) "
            "OPTIONAL MATCH (m:Memory)-[:CONTRIBUTES_TO]->(s) "
            "OPTIONAL MATCH (s)-[:COVERS]->(e:Entity) "
            "RETURN s.id AS id, s.topic AS topic, s.summary AS summary, "
            "s.key_findings AS key_findings, "
            "collect(DISTINCT m.id) AS memory_ids, "
            "collect(DISTINCT e.key) AS entity_keys"
        )
        syntheses = [dict(r) for r in result]

    driver.close()

    print(f"Found {len(memories)} memories and {len(syntheses)} syntheses locally.", file=sys.stderr)

    if not memories:
        _print_json({"message": "No local memories to migrate", "count": 0})
        return

    if args.dry_run:
        _print_json({
            "dry_run": True,
            "memories": len(memories),
            "syntheses": len(syntheses),
            "sample_titles": [m["title"] for m in memories[:5]],
        })
        return

    # Upload to cloud
    client = _get_client()
    uploaded = 0
    errors = []

    for mem in memories:
        try:
            client.store_memory(
                title=mem["title"],
                summary=mem["summary"],
                workflow=mem["workflow"] or "",
                tools_used=mem["tools_used"] or [],
                categories=mem["categories"] or [],
                project=mem["project"] or "",
                session_id=mem["session_id"] or "",
            )
            uploaded += 1
        except Exception as e:
            errors.append({"title": mem["title"], "error": str(e)})

    # Upload syntheses (need to map old memory IDs to new ones)
    synth_uploaded = 0
    for synth in syntheses:
        try:
            client.create_synthesis(
                topic=synth["topic"],
                summary=synth["summary"],
                key_findings=synth["key_findings"] or "",
                memory_ids=[],  # Can't map old IDs; link by entity keys instead
                entity_keys=synth["entity_keys"] or [],
            )
            synth_uploaded += 1
        except Exception:
            pass

    _print_json({
        "migrated": True,
        "memories_uploaded": uploaded,
        "syntheses_uploaded": synth_uploaded,
        "errors": errors,
    })


# ── Sync Commands ────────────────────────────────────────────────────

def cmd_sync(args):
    """Sync local memories to the global graph (sanitized)."""
    client = _get_client()

    # Get all user memories
    all_memories = []
    offset = 0
    batch_size = 50
    while True:
        result = client._get("/api/memories", limit=batch_size, offset=offset)
        batch = result.get("memories", [])
        if not batch:
            break
        all_memories.extend(batch)
        offset += batch_size

    if not all_memories:
        print(json.dumps({"message": "No memories to sync", "count": 0}))
        return

    # Sanitize each memory
    sanitized = [sanitize_memory(m) for m in all_memories]

    if args.dry_run:
        # Show what would change
        diffs = []
        for orig, san in zip(all_memories, sanitized):
            diff = preview_diff(orig)
            if diff:
                diffs.append({"id": orig.get("id", "?"), "title": orig.get("title", "?"), "changes": diff})
        _print_json({"dry_run": True, "memories_to_sync": len(sanitized), "changes": diffs})
        return

    # Push to global
    result = client.sync_memories(sanitized)
    _print_json({"synced": True, **result})


# ── Global Commands ──────────────────────────────────────────────────

def cmd_global_search(args):
    """Search the global knowledge graph."""
    client = _get_client()
    results = client.search_global(args.query, limit=args.limit)
    _print_json({"results": results})


def cmd_global_browse(args):
    """Browse global categories."""
    client = _get_client()
    result = client.browse_global()
    _print_json(result)


def cmd_global_stats(args):
    """Show global graph statistics."""
    client = _get_client()
    result = client.get_global_stats()
    _print_json(result)


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Hivemind CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # auth
    auth_p = subparsers.add_parser("auth", help="Authentication management")
    auth_sub = auth_p.add_subparsers(dest="auth_command", required=True)

    set_key_p = auth_sub.add_parser("set-key", help="Store API key")
    set_key_p.add_argument("key", help="API key from the web dashboard")

    auth_sub.add_parser("status", help="Check auth status")
    auth_sub.add_parser("clear-key", help="Remove stored API key")

    # categories
    subparsers.add_parser("categories", help="List category tree")

    # store
    store_p = subparsers.add_parser("store", help="Store a memory")
    store_p.add_argument("--json", required=True, help="JSON memory data")

    # search
    search_p = subparsers.add_parser("search", help="Search memories")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--limit", type=int, default=5)

    # search-category
    cat_search_p = subparsers.add_parser("search-category", help="Browse by category")
    cat_search_p.add_argument("category", help="Category name")
    cat_search_p.add_argument("--limit", type=int, default=10)

    # get
    get_p = subparsers.add_parser("get", help="Get memory details")
    get_p.add_argument("id", help="Memory ID")

    # search-expanded
    exp_p = subparsers.add_parser("search-expanded", help="Search with graph expansion")
    exp_p.add_argument("query", help="Search query")
    exp_p.add_argument("--limit", type=int, default=5)
    exp_p.add_argument("--expansion-limit", type=int, default=5)

    # backfill-entities
    subparsers.add_parser("backfill-entities", help="Backfill entity extraction")

    # log
    log_p = subparsers.add_parser("log", help="View activity log")
    log_p.add_argument("--limit", type=int, default=20)
    log_p.add_argument("--action", default="", help="Filter by action type")

    # synthesize
    synth_p = subparsers.add_parser("synthesize", help="Create a synthesis node")
    synth_p.add_argument("--json", required=True, help="JSON synthesis data")

    # list-syntheses
    ls_p = subparsers.add_parser("list-syntheses", help="List synthesis nodes")
    ls_p.add_argument("--limit", type=int, default=20)

    # get-synthesis
    gs_p = subparsers.add_parser("get-synthesis", help="Get synthesis details")
    gs_p.add_argument("id", help="Synthesis ID")

    # find-synthesis-gaps
    fsg_p = subparsers.add_parser("find-synthesis-gaps", help="Find knowledge gaps")
    fsg_p.add_argument("--min-memories", type=int, default=3)

    # lint
    subparsers.add_parser("lint", help="Run graph health check")

    # transcript
    trans_p = subparsers.add_parser("transcript", help="Read session transcript")
    trans_p.add_argument("session_id", help="Session ID")
    trans_p.add_argument("project_path", help="Project path")

    # migrate
    migrate_p = subparsers.add_parser("migrate", help="Migrate local Neo4j memories to cloud")
    migrate_p.add_argument("--dry-run", action="store_true", help="Preview what would be migrated")

    # sync
    sync_p = subparsers.add_parser("sync", help="Sync memories to global graph")
    sync_p.add_argument("--dry-run", action="store_true", help="Preview sanitization")

    # global
    global_p = subparsers.add_parser("global", help="Global knowledge graph")
    global_sub = global_p.add_subparsers(dest="global_command", required=True)

    gsearch_p = global_sub.add_parser("search", help="Search global graph")
    gsearch_p.add_argument("query", help="Search query")
    gsearch_p.add_argument("--limit", type=int, default=10)

    global_sub.add_parser("browse", help="Browse global categories")
    global_sub.add_parser("stats", help="Global graph statistics")

    args = parser.parse_args()

    # Route auth subcommands
    if args.command == "auth":
        auth_commands = {
            "set-key": cmd_auth_set_key,
            "status": cmd_auth_status,
            "clear-key": cmd_auth_clear_key,
        }
        try:
            auth_commands[args.auth_command](args)
        except Exception as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        return

    # Route global subcommands
    if args.command == "global":
        global_commands = {
            "search": cmd_global_search,
            "browse": cmd_global_browse,
            "stats": cmd_global_stats,
        }
        try:
            global_commands[args.global_command](args)
        except Exception as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        finally:
            cloud_client.close()
        return

    commands = {
        "categories": cmd_categories,
        "store": cmd_store,
        "search": cmd_search,
        "search-category": cmd_search_category,
        "search-expanded": cmd_search_expanded,
        "backfill-entities": cmd_backfill_entities,
        "log": cmd_log,
        "synthesize": cmd_synthesize,
        "list-syntheses": cmd_list_syntheses,
        "get-synthesis": cmd_get_synthesis,
        "find-synthesis-gaps": cmd_find_synthesis_gaps,
        "lint": cmd_lint,
        "get": cmd_get,
        "transcript": cmd_transcript,
        "migrate": cmd_migrate,
        "sync": cmd_sync,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    finally:
        cloud_client.close()


if __name__ == "__main__":
    main()
