#!/usr/bin/env python3
"""MCP server for Hivemind session memory system.

Cloud-first: all operations go through the cloud API via cloud_client.
Registered in ~/.claude/settings.json for use by all sessions and sub-agents.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
import cloud_client
from core.sanitizer import sanitize_memory

mcp = FastMCP("hivemind")

# Auto-provision on startup (best-effort)
try:
    cloud_client.get_client().ensure_provisioned()
except Exception:
    pass


def _client():
    return cloud_client.get_client()


@mcp.tool()
def store_memory(
    title: str,
    summary: str,
    workflow: str,
    tools_used: list,
    categories: list,
    project: str = "",
    session_id: str = "",
) -> dict:
    """Store a new memory capturing a problem-solving pattern.

    Use this to record interesting debugging workflows, error recoveries,
    architectural decisions, or tool usage patterns from the current session.

    Args:
        title: Short descriptive title (e.g., "Fix circular import with lazy loading")
        summary: 2-3 sentence description of the problem, approach, and outcome
        workflow: Step-by-step description of what was done
        tools_used: List of tools used (e.g., ["Grep", "Edit", "Bash"])
        categories: Hierarchical categories in kebab-case (e.g., ["debugging", "debugging/import-errors"])
        project: Project path (optional, auto-censored in global sync)
        session_id: Session identifier (optional)
    """
    memory_id = _client().store_memory(
        title=title, summary=summary, workflow=workflow,
        tools_used=tools_used, categories=categories,
        project=project, session_id=session_id,
    )
    return {"id": memory_id, "stored": True}


@mcp.tool()
def search_memories(query: str, limit: int = 5) -> dict:
    """Search session memories by text query.

    Searches across memory titles, summaries, and workflows using full-text search.
    Use this when encountering errors, debugging issues, or working with specific
    tools/frameworks — past sessions may have captured relevant patterns.

    Args:
        query: Search text (e.g., "import error", "neo4j connection", "git rebase")
        limit: Maximum number of results to return (default 5)
    """
    results = _client().search_memories(query, limit=limit)
    return {"results": results, "count": len(results)}


@mcp.tool()
def browse_categories() -> dict:
    """Get the full category tree of stored memories.

    Returns all categories organized hierarchically. Use this to understand
    what kinds of memories are available before searching.
    """
    categories = _client().get_categories()
    return {"categories": categories}


@mcp.tool()
def get_memory(id: str) -> dict:
    """Get full details of a specific memory by ID.

    Returns the complete memory including title, summary, step-by-step workflow,
    tools used, categories, and source session info.

    Args:
        id: The UUID of the memory to retrieve
    """
    result = _client().get_memory(id)
    if result is None:
        return {"error": "Memory not found"}
    return {"memory": result}


@mcp.tool()
def get_memories_for_task(task_description: str, limit: int = 5) -> dict:
    """Find memories relevant to a specific task you're about to work on.

    PROACTIVE USE: Call this tool early when starting a debugging task, fixing
    an error, or working on a non-trivial problem. Past sessions may have solved
    similar issues — checking first avoids re-discovering solutions from scratch.

    Returns memories with their full step-by-step workflows so you can follow
    proven patterns.

    Args:
        task_description: Description of the task (e.g., "fix circular import in Python project")
        limit: Maximum number of results (default 5)
    """
    client = _client()
    results = client.search_memories(task_description, limit=limit)
    enriched = []
    for r in results[:limit]:
        full = client.get_memory(r["id"])
        if full:
            enriched.append(full)
    return {"memories": enriched, "count": len(enriched)}


@mcp.tool()
def search_with_expansion(query: str, limit: int = 5, expansion_limit: int = 5) -> dict:
    """Search memories with graph-based expansion via shared entities.

    First performs full-text search to find seed memories, then expands via
    entities (libraries, error types, concepts, frameworks) shared between
    memories. This surfaces related memories that may not match the text
    query but are connected by topic through the knowledge graph.

    Args:
        query: Search text (e.g., "neo4j connection error")
        limit: Maximum seed results from text search (default 5)
        expansion_limit: Maximum additional results from graph expansion (default 5)
    """
    return _client().search_with_expansion(query, limit=limit, expansion_limit=expansion_limit)


@mcp.tool()
def search_by_category(category: str, limit: int = 10) -> dict:
    """Browse memories in a specific category.

    Returns memories belonging to the given category and its children.
    Use browse_categories() first to see available categories.

    Args:
        category: Category name in kebab-case (e.g., "debugging", "error-recovery")
        limit: Maximum number of results (default 10)
    """
    results = _client().search_by_category(category, limit=limit)
    return {"results": results, "count": len(results)}


@mcp.tool()
def view_log(limit: int = 20, action: str = "") -> dict:
    """Browse the activity log of all Hivemind operations.

    Shows chronological record of memory storage, synthesis creation/updates,
    lint runs, and query promotions.

    Args:
        limit: Maximum entries to return (default 20)
        action: Filter by action type (e.g., "memory_stored", "synthesis_created", "lint_run")
    """
    entries = _client().get_log(limit=limit, action_filter=action or None)
    return {"entries": entries, "count": len(entries)}


@mcp.tool()
def synthesize_topic(topic: str, summary: str, key_findings: str, memory_ids: list, entity_keys: list = None) -> dict:
    """Create a Synthesis node that aggregates knowledge across multiple memories.

    Synthesis nodes are the wiki layer — living summary pages that compound
    knowledge over time. Call this when you identify a pattern across memories
    or after find_synthesis_gaps reveals uncovered entity clusters.

    Args:
        topic: Topic name (e.g., "Neo4j Connection Patterns")
        summary: Multi-sentence synthesis of the knowledge
        key_findings: Bullet-point key findings
        memory_ids: List of Memory UUIDs that contribute to this synthesis
        entity_keys: Optional list of Entity keys (type:name) this synthesis covers
    """
    sid = _client().create_synthesis(topic, summary, key_findings, memory_ids, entity_keys)
    return {"id": sid, "topic": topic, "memories_linked": len(memory_ids)}


@mcp.tool()
def update_synthesis_node(synthesis_id: str, summary: str = "", key_findings: str = "", add_memory_ids: list = None) -> dict:
    """Update an existing Synthesis node with new content or contributing memories.

    Call this when new memories add to an existing synthesis topic.

    Args:
        synthesis_id: UUID of the Synthesis to update
        summary: Updated summary (empty string to keep current)
        key_findings: Updated key findings (empty string to keep current)
        add_memory_ids: Additional Memory UUIDs to link
    """
    _client().update_synthesis(
        synthesis_id,
        summary=summary or None,
        key_findings=key_findings or None,
        add_memory_ids=add_memory_ids,
    )
    return {"updated": True, "id": synthesis_id}


@mcp.tool()
def list_syntheses(limit: int = 20) -> dict:
    """List all synthesis pages, most recently updated first.

    Syntheses are aggregated knowledge pages that summarize patterns across
    multiple memories on a topic.

    Args:
        limit: Maximum results (default 20)
    """
    results = _client().list_syntheses(limit=limit)
    return {"syntheses": results, "count": len(results)}


@mcp.tool()
def get_synthesis_detail(id: str) -> dict:
    """Get full details of a Synthesis node including contributing memories and entities.

    Args:
        id: UUID of the Synthesis
    """
    result = _client().get_synthesis(id)
    if result is None:
        return {"error": "Synthesis not found"}
    return {"synthesis": result}


@mcp.tool()
def find_synthesis_gaps(min_memories: int = 3) -> dict:
    """Find entity clusters with enough memories but no Synthesis node yet.

    These are knowledge gaps — topics where memories exist but no one has
    written a synthesis page yet. Use synthesize_topic to fill the gaps.

    Args:
        min_memories: Minimum memories sharing an entity to count as a gap (default 3)
    """
    gaps = _client().find_synthesis_gaps(min_memories=min_memories)
    return {"gaps": gaps, "count": len(gaps)}


@mcp.tool()
def promote_query(query: str, answer: str, memory_ids: list) -> dict:
    """Promote a valuable query result to a permanent Synthesis node.

    When a search produces an insightful answer worth preserving, call this
    to create a Synthesis node from the query and its answer.

    Args:
        query: The original search query
        answer: The synthesized answer worth preserving
        memory_ids: List of Memory UUIDs that contributed to the answer
    """
    client = _client()
    sid = client.create_synthesis(
        topic=query,
        summary=answer,
        key_findings="Promoted from query result",
        memory_ids=memory_ids,
    )
    client.append_log("query_promoted", f"query={query}, synthesis={sid}")
    return {"id": sid, "topic": query, "promoted": True}


@mcp.tool()
def lint_graph() -> dict:
    """Run health checks on the knowledge graph.

    Identifies: orphaned memories (no entities), stale syntheses, disconnected
    entities, category imbalance, knowledge gaps, and potential duplicates.
    """
    return _client().lint()


# ── New: Global Graph Tools ──────────────────────────────────────────

@mcp.tool()
def sync_to_global() -> dict:
    """Sync your memories to the global knowledge graph.

    Pushes all your memories to the shared global graph after sanitizing
    private information (file paths, repo names, project identifiers).
    Other users can then search and learn from your anonymized patterns.
    """
    client = _client()

    # Fetch all user memories
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
        return {"message": "No memories to sync", "count": 0}

    sanitized = [sanitize_memory(m) for m in all_memories]
    result = client.sync_memories(sanitized)
    return {"synced": True, "count": len(sanitized), **result}


@mcp.tool()
def search_global(query: str, limit: int = 10) -> dict:
    """Search the global knowledge graph for shared patterns and solutions.

    The global graph contains sanitized memories from all users. File paths
    and repository names are anonymized, but the problem-solving patterns,
    tool usage, and debugging strategies are preserved.

    Args:
        query: Search text (e.g., "circular import fix", "neo4j performance")
        limit: Maximum results (default 10)
    """
    results = _client().search_global(query, limit=limit)
    return {"results": results, "count": len(results)}


@mcp.tool()
def browse_global() -> dict:
    """Browse categories in the global knowledge graph.

    Shows what topics the community has contributed knowledge about.
    """
    return _client().browse_global()


if __name__ == "__main__":
    mcp.run(transport="stdio")
