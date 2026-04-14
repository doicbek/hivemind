"""Local SQLite-backed client for Hivemind.

Drop-in replacement for HivemindClient when running in local mode.
Uses SQLite with FTS5 for full-text search. No network calls.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

import config
from core.entity_extractor import extract_entities


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    workflow TEXT NOT NULL DEFAULT '',
    tools_used TEXT NOT NULL DEFAULT '[]',
    categories TEXT NOT NULL DEFAULT '[]',
    project TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    name TEXT PRIMARY KEY,
    display_name TEXT,
    description TEXT DEFAULT '',
    level INTEGER DEFAULT 0,
    parent_name TEXT
);

CREATE TABLE IF NOT EXISTS memory_categories (
    memory_id TEXT NOT NULL REFERENCES memories(id),
    category_name TEXT NOT NULL REFERENCES categories(name),
    PRIMARY KEY (memory_id, category_name)
);

CREATE TABLE IF NOT EXISTS entities (
    key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_entities (
    memory_id TEXT NOT NULL REFERENCES memories(id),
    entity_key TEXT NOT NULL REFERENCES entities(key),
    PRIMARY KEY (memory_id, entity_key)
);

CREATE TABLE IF NOT EXISTS syntheses (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_findings TEXT NOT NULL DEFAULT '',
    memory_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS synthesis_memories (
    synthesis_id TEXT NOT NULL REFERENCES syntheses(id),
    memory_id TEXT NOT NULL REFERENCES memories(id),
    PRIMARY KEY (synthesis_id, memory_id)
);

CREATE TABLE IF NOT EXISTS synthesis_entities (
    synthesis_id TEXT NOT NULL REFERENCES syntheses(id),
    entity_key TEXT NOT NULL REFERENCES entities(key),
    PRIMARY KEY (synthesis_id, entity_key)
);

CREATE TABLE IF NOT EXISTS log_entries (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    detail TEXT DEFAULT '',
    timestamp TEXT NOT NULL
);
"""

_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    title, summary, workflow,
    content='memories', content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS syntheses_fts USING fts5(
    topic, summary, key_findings,
    content='syntheses', content_rowid='rowid'
);
"""

_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, title, summary, workflow)
    VALUES (new.rowid, new.title, new.summary, new.workflow);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, title, summary, workflow)
    VALUES ('delete', old.rowid, old.title, old.summary, old.workflow);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, title, summary, workflow)
    VALUES ('delete', old.rowid, old.title, old.summary, old.workflow);
    INSERT INTO memories_fts(rowid, title, summary, workflow)
    VALUES (new.rowid, new.title, new.summary, new.workflow);
END;

CREATE TRIGGER IF NOT EXISTS syntheses_ai AFTER INSERT ON syntheses BEGIN
    INSERT INTO syntheses_fts(rowid, topic, summary, key_findings)
    VALUES (new.rowid, new.topic, new.summary, new.key_findings);
END;

CREATE TRIGGER IF NOT EXISTS syntheses_ad AFTER DELETE ON syntheses BEGIN
    INSERT INTO syntheses_fts(syntheses_fts, rowid, topic, summary, key_findings)
    VALUES ('delete', old.rowid, old.topic, old.summary, old.key_findings);
END;

CREATE TRIGGER IF NOT EXISTS syntheses_au AFTER UPDATE ON syntheses BEGIN
    INSERT INTO syntheses_fts(syntheses_fts, rowid, topic, summary, key_findings)
    VALUES ('delete', old.rowid, old.topic, old.summary, old.key_findings);
    INSERT INTO syntheses_fts(rowid, topic, summary, key_findings)
    VALUES (new.rowid, new.topic, new.summary, new.key_findings);
END;
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _parse_category_path(path: str):
    """Parse 'debugging/import-errors' into category entries."""
    parts = path.strip("/").split("/")
    entries = []
    for i, part in enumerate(parts):
        name = "/".join(parts[: i + 1])
        parent = "/".join(parts[:i]) if i > 0 else None
        display = part.replace("-", " ").title()
        entries.append({"name": name, "display_name": display, "level": i, "parent_name": parent})
    return entries


class LocalClient:
    """SQLite-backed local client with the same interface as HivemindClient."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or config.get_db_path()
        self.api_key = None  # Local mode has no API key
        self._conn = None
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _ensure_schema(self):
        conn = self._get_conn()
        conn.executescript(_SCHEMA_SQL)
        conn.executescript(_FTS_SQL)
        conn.executescript(_TRIGGERS_SQL)
        conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Auth ─────────────────────────────────────────────────────────

    def auth_status(self) -> dict:
        return {"authenticated": True, "mode": "local", "db_path": self.db_path}

    # ── Memories ─────────────────────────────────────────────────────

    def store_memory(
        self,
        title: str,
        summary: str,
        workflow: str,
        tools_used: list[str],
        categories: list[str],
        project: str = "",
        session_id: str = "",
        user_id: str | None = None,
    ) -> str:
        conn = self._get_conn()
        memory_id = str(uuid.uuid4())
        now = _now()

        conn.execute(
            "INSERT INTO memories (id, title, summary, workflow, tools_used, categories, project, session_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (memory_id, title, summary, workflow, json.dumps(tools_used), json.dumps(categories), project, session_id, now),
        )

        # Categories
        for cat_path in categories:
            for entry in _parse_category_path(cat_path):
                conn.execute(
                    "INSERT OR IGNORE INTO categories (name, display_name, level, parent_name) VALUES (?, ?, ?, ?)",
                    (entry["name"], entry["display_name"], entry["level"], entry["parent_name"]),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO memory_categories (memory_id, category_name) VALUES (?, ?)",
                    (memory_id, entry["name"]),
                )

        # Entities
        extracted = extract_entities(title, summary, workflow)
        for ent in extracted:
            key = f"{ent['type']}:{ent['name']}"
            conn.execute(
                "INSERT OR IGNORE INTO entities (key, name, type) VALUES (?, ?, ?)",
                (key, ent["name"], ent["type"]),
            )
            conn.execute(
                "INSERT OR IGNORE INTO memory_entities (memory_id, entity_key) VALUES (?, ?)",
                (memory_id, key),
            )

        # Log
        self._log(conn, "memory_stored", f"Stored: {title}")
        conn.commit()
        return memory_id

    def search_memories(self, query: str, limit: int = 5) -> list[dict]:
        conn = self._get_conn()
        # Escape FTS5 special characters by quoting the query
        safe_query = '"' + query.replace('"', '""') + '"'
        rows = conn.execute(
            "SELECT m.id, m.title, m.summary, m.tools_used, m.project, m.created_at "
            "FROM memories m JOIN memories_fts f ON m.rowid = f.rowid "
            "WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?",
            (safe_query, limit),
        ).fetchall()
        return [self._memory_row_to_dict(r) for r in rows]

    def search_with_expansion(self, query: str, limit: int = 5, expansion_limit: int = 5) -> dict:
        seeds = self.search_memories(query, limit)
        if not seeds:
            return {"seeds": [], "expanded": []}

        conn = self._get_conn()
        seed_ids = [s["id"] for s in seeds]
        placeholders = ",".join("?" * len(seed_ids))

        # Find entities from seed memories
        entity_rows = conn.execute(
            f"SELECT DISTINCT entity_key FROM memory_entities WHERE memory_id IN ({placeholders})",
            seed_ids,
        ).fetchall()
        entity_keys = [r["entity_key"] for r in entity_rows]

        if not entity_keys:
            return {"seeds": seeds, "expanded": []}

        # Find other memories sharing those entities
        ek_placeholders = ",".join("?" * len(entity_keys))
        expanded_rows = conn.execute(
            f"SELECT m.id, m.title, m.summary, m.tools_used, m.project, m.created_at, "
            f"COUNT(me.entity_key) AS shared_entities "
            f"FROM memories m JOIN memory_entities me ON m.id = me.memory_id "
            f"WHERE me.entity_key IN ({ek_placeholders}) AND m.id NOT IN ({placeholders}) "
            f"GROUP BY m.id ORDER BY shared_entities DESC LIMIT ?",
            entity_keys + seed_ids + [expansion_limit],
        ).fetchall()

        expanded = [self._memory_row_to_dict(r) for r in expanded_rows]
        return {"seeds": seeds, "expanded": expanded}

    def search_by_category(self, category: str, limit: int = 10) -> list[dict]:
        conn = self._get_conn()
        # Match exact category or children (e.g., "debugging" matches "debugging/import-errors")
        rows = conn.execute(
            "SELECT DISTINCT m.id, m.title, m.summary, m.tools_used, m.project, m.created_at "
            "FROM memories m JOIN memory_categories mc ON m.id = mc.memory_id "
            "WHERE mc.category_name = ? OR mc.category_name LIKE ? "
            "ORDER BY m.created_at DESC LIMIT ?",
            (category, category + "/%", limit),
        ).fetchall()
        return [self._memory_row_to_dict(r) for r in rows]

    def get_memory(self, memory_id: str) -> dict | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if not row:
            return None

        cats = conn.execute(
            "SELECT category_name FROM memory_categories WHERE memory_id = ?", (memory_id,)
        ).fetchall()
        ents = conn.execute(
            "SELECT e.key, e.name, e.type FROM entities e "
            "JOIN memory_entities me ON e.key = me.entity_key "
            "WHERE me.memory_id = ?", (memory_id,)
        ).fetchall()

        return {
            "id": row["id"],
            "title": row["title"],
            "summary": row["summary"],
            "workflow": row["workflow"],
            "tools_used": json.loads(row["tools_used"]),
            "categories": [c["category_name"] for c in cats],
            "entities": [{"key": e["key"], "name": e["name"], "type": e["type"]} for e in ents],
            "project": row["project"],
            "session_id": row["session_id"],
            "created_at": row["created_at"],
        }

    def get_categories(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT c.name, c.display_name, c.description, c.level, c.parent_name, "
            "COUNT(mc.memory_id) AS memory_count "
            "FROM categories c LEFT JOIN memory_categories mc ON c.name = mc.category_name "
            "GROUP BY c.name ORDER BY c.level, c.name"
        ).fetchall()
        return [
            {
                "name": r["name"], "display_name": r["display_name"],
                "description": r["description"], "level": r["level"],
                "parent_name": r["parent_name"], "memory_count": r["memory_count"],
            }
            for r in rows
        ]

    # ── Synthesis ────────────────────────────────────────────────────

    def create_synthesis(
        self,
        topic: str,
        summary: str,
        key_findings: str,
        memory_ids: list[str],
        entity_keys: list[str] | None = None,
    ) -> str:
        conn = self._get_conn()
        synthesis_id = str(uuid.uuid4())
        now = _now()

        conn.execute(
            "INSERT INTO syntheses (id, topic, summary, key_findings, memory_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (synthesis_id, topic, summary, key_findings, len(memory_ids), now, now),
        )
        for mid in memory_ids:
            conn.execute(
                "INSERT OR IGNORE INTO synthesis_memories (synthesis_id, memory_id) VALUES (?, ?)",
                (synthesis_id, mid),
            )
        for ek in (entity_keys or []):
            conn.execute(
                "INSERT OR IGNORE INTO synthesis_entities (synthesis_id, entity_key) VALUES (?, ?)",
                (synthesis_id, ek),
            )

        self._log(conn, "synthesis_created", f"Synthesized: {topic}")
        conn.commit()
        return synthesis_id

    def update_synthesis(
        self,
        synthesis_id: str,
        summary: str | None = None,
        key_findings: str | None = None,
        add_memory_ids: list[str] | None = None,
    ) -> dict:
        conn = self._get_conn()
        now = _now()

        if summary is not None:
            conn.execute("UPDATE syntheses SET summary = ?, updated_at = ? WHERE id = ?", (summary, now, synthesis_id))
        if key_findings is not None:
            conn.execute("UPDATE syntheses SET key_findings = ?, updated_at = ? WHERE id = ?", (key_findings, now, synthesis_id))
        if add_memory_ids:
            for mid in add_memory_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO synthesis_memories (synthesis_id, memory_id) VALUES (?, ?)",
                    (synthesis_id, mid),
                )
            # Update memory_count
            count = conn.execute(
                "SELECT COUNT(*) AS c FROM synthesis_memories WHERE synthesis_id = ?", (synthesis_id,)
            ).fetchone()["c"]
            conn.execute("UPDATE syntheses SET memory_count = ?, updated_at = ? WHERE id = ?", (count, now, synthesis_id))

        conn.commit()
        return {"updated": True, "id": synthesis_id}

    def get_synthesis(self, synthesis_id: str) -> dict | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM syntheses WHERE id = ?", (synthesis_id,)).fetchone()
        if not row:
            return None

        mems = conn.execute(
            "SELECT memory_id FROM synthesis_memories WHERE synthesis_id = ?", (synthesis_id,)
        ).fetchall()
        ents = conn.execute(
            "SELECT entity_key FROM synthesis_entities WHERE synthesis_id = ?", (synthesis_id,)
        ).fetchall()

        return {
            "id": row["id"], "topic": row["topic"], "summary": row["summary"],
            "key_findings": row["key_findings"], "memory_count": row["memory_count"],
            "memory_ids": [m["memory_id"] for m in mems],
            "entity_keys": [e["entity_key"] for e in ents],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
        }

    def list_syntheses(self, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, topic, summary, memory_count, created_at, updated_at "
            "FROM syntheses ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def find_synthesis_gaps(self, min_memories: int = 3) -> list[dict]:
        conn = self._get_conn()
        # Entities linked to >= min_memories memories but not covered by any synthesis
        rows = conn.execute(
            "SELECT e.key AS entity_key, e.name AS entity_name, e.type AS entity_type, "
            "COUNT(DISTINCT me.memory_id) AS memory_count, "
            "GROUP_CONCAT(DISTINCT me.memory_id) AS memory_ids "
            "FROM entities e "
            "JOIN memory_entities me ON e.key = me.entity_key "
            "LEFT JOIN synthesis_entities se ON e.key = se.entity_key "
            "WHERE se.entity_key IS NULL "
            "GROUP BY e.key HAVING COUNT(DISTINCT me.memory_id) >= ? "
            "ORDER BY memory_count DESC",
            (min_memories,),
        ).fetchall()
        return [
            {
                "entity_key": r["entity_key"], "entity_name": r["entity_name"],
                "entity_type": r["entity_type"], "memory_count": r["memory_count"],
                "memory_ids": r["memory_ids"].split(",") if r["memory_ids"] else [],
            }
            for r in rows
        ]

    # ── Graph + Stats ────────────────────────────────────────────────

    def get_graph_data(self, node_types: list[str] | None = None, limit: int = 500) -> dict:
        conn = self._get_conn()
        nodes = {}
        edges = []

        if not node_types or "Memory" in node_types:
            rows = conn.execute(
                "SELECT id, title, summary FROM memories ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            for r in rows:
                nodes[r["id"]] = {"id": r["id"], "type": "Memory", "label": r["title"], "summary": r["summary"]}

        if not node_types or "Category" in node_types:
            rows = conn.execute(
                "SELECT DISTINCT c.name, c.display_name, c.level "
                "FROM categories c JOIN memory_categories mc ON c.name = mc.category_name"
            ).fetchall()
            for r in rows:
                nid = f"cat:{r['name']}"
                nodes[nid] = {"id": nid, "type": "Category", "label": r["display_name"] or r["name"], "level": r["level"]}

        if not node_types or "Tool" in node_types:
            # Tools are stored in memory's tools_used JSON — extract unique names
            rows = conn.execute("SELECT tools_used FROM memories").fetchall()
            tool_names = set()
            for r in rows:
                for t in json.loads(r["tools_used"]):
                    tool_names.add(t)
            for name in tool_names:
                nid = f"tool:{name}"
                nodes[nid] = {"id": nid, "type": "Tool", "label": name}

        if not node_types or "Entity" in node_types:
            rows = conn.execute(
                "SELECT DISTINCT e.key, e.name, e.type "
                "FROM entities e JOIN memory_entities me ON e.key = me.entity_key"
            ).fetchall()
            for r in rows:
                nid = f"entity:{r['key']}"
                nodes[nid] = {"id": nid, "type": "Entity", "label": r["name"], "entity_type": r["type"]}

        # Edges: memory → category
        for r in conn.execute(
            "SELECT memory_id, category_name FROM memory_categories"
        ).fetchall():
            if r["memory_id"] in nodes:
                edges.append({"source": r["memory_id"], "target": f"cat:{r['category_name']}", "type": "BELONGS_TO"})

        # Edges: memory → entity
        for r in conn.execute("SELECT memory_id, entity_key FROM memory_entities").fetchall():
            if r["memory_id"] in nodes:
                edges.append({"source": r["memory_id"], "target": f"entity:{r['entity_key']}", "type": "MENTIONS"})

        # Edges: memory → tool (from JSON field)
        for r in conn.execute("SELECT id, tools_used FROM memories").fetchall():
            if r["id"] in nodes:
                for t in json.loads(r["tools_used"]):
                    edges.append({"source": r["id"], "target": f"tool:{t}", "type": "USES_TOOL"})

        # Edges: category → parent category
        cat_names = {nid[4:] for nid in nodes if nid.startswith("cat:")}
        for r in conn.execute(
            "SELECT name, parent_name FROM categories WHERE parent_name IS NOT NULL"
        ).fetchall():
            if r["name"] in cat_names or r["parent_name"] in cat_names:
                edges.append({"source": f"cat:{r['parent_name']}", "target": f"cat:{r['name']}", "type": "PARENT_OF"})

        # Synthesis nodes and edges
        if not node_types or "Synthesis" in node_types:
            rows = conn.execute(
                "SELECT id, topic, summary, memory_count FROM syntheses"
            ).fetchall()
            for r in rows:
                nid = f"synth:{r['id']}"
                nodes[nid] = {"id": nid, "type": "Synthesis", "label": r["topic"], "summary": r["summary"], "memory_count": r["memory_count"]}

            for r in conn.execute("SELECT synthesis_id, memory_id FROM synthesis_memories").fetchall():
                if r["memory_id"] in nodes:
                    edges.append({"source": r["memory_id"], "target": f"synth:{r['synthesis_id']}", "type": "CONTRIBUTES_TO"})

            for r in conn.execute("SELECT synthesis_id, entity_key FROM synthesis_entities").fetchall():
                edges.append({"source": f"synth:{r['synthesis_id']}", "target": f"entity:{r['entity_key']}", "type": "COVERS"})

        return {"nodes": list(nodes.values()), "edges": edges}

    def get_stats(self) -> dict:
        conn = self._get_conn()
        mem_count = conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()["c"]
        synth_count = conn.execute("SELECT COUNT(*) AS c FROM syntheses").fetchone()["c"]
        cat_count = conn.execute(
            "SELECT COUNT(DISTINCT c.name) AS c FROM categories c "
            "JOIN memory_categories mc ON c.name = mc.category_name"
        ).fetchone()["c"]
        tool_count = len({
            t for r in conn.execute("SELECT tools_used FROM memories").fetchall()
            for t in json.loads(r["tools_used"])
        })
        entity_count = conn.execute(
            "SELECT COUNT(DISTINCT entity_key) AS c FROM memory_entities"
        ).fetchone()["c"]

        top_entities = conn.execute(
            "SELECT e.name, e.type, COUNT(me.memory_id) AS mentions "
            "FROM entities e JOIN memory_entities me ON e.key = me.entity_key "
            "GROUP BY e.key ORDER BY mentions DESC LIMIT 20"
        ).fetchall()

        return {
            "node_counts": {
                "Memory": mem_count, "Synthesis": synth_count,
                "Category": cat_count, "Tool": tool_count, "Entity": entity_count,
            },
            "top_entities": [dict(r) for r in top_entities],
        }

    # ── Log ──────────────────────────────────────────────────────────

    def get_log(self, limit: int = 20, action_filter: str | None = None) -> list[dict]:
        conn = self._get_conn()
        if action_filter:
            rows = conn.execute(
                "SELECT * FROM log_entries WHERE action = ? ORDER BY timestamp DESC LIMIT ?",
                (action_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM log_entries ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def append_log(self, action: str, detail: str = "") -> str:
        conn = self._get_conn()
        log_id = self._log(conn, action, detail)
        conn.commit()
        return log_id

    # ── Lint ─────────────────────────────────────────────────────────

    def lint(self) -> dict:
        conn = self._get_conn()
        issues = []

        # Orphaned memories (no entities)
        orphaned = conn.execute(
            "SELECT m.id, m.title FROM memories m "
            "LEFT JOIN memory_entities me ON m.id = me.memory_id "
            "WHERE me.memory_id IS NULL"
        ).fetchall()
        if orphaned:
            issues.append({
                "type": "orphaned_memories",
                "message": f"{len(orphaned)} memories with no extracted entities",
                "ids": [r["id"] for r in orphaned],
            })

        # Stale synthesis counts
        stale = conn.execute(
            "SELECT s.id, s.topic, s.memory_count, COUNT(sm.memory_id) AS actual "
            "FROM syntheses s LEFT JOIN synthesis_memories sm ON s.id = sm.synthesis_id "
            "GROUP BY s.id HAVING s.memory_count != actual"
        ).fetchall()
        if stale:
            issues.append({
                "type": "stale_synthesis_counts",
                "message": f"{len(stale)} syntheses with incorrect memory counts",
                "ids": [r["id"] for r in stale],
            })

        # Synthesis gaps
        gaps = self.find_synthesis_gaps(min_memories=3)
        if gaps:
            issues.append({
                "type": "synthesis_gaps",
                "message": f"{len(gaps)} entity clusters lacking synthesis",
                "entities": [g["entity_key"] for g in gaps[:10]],
            })

        self._log(conn, "lint_run", f"Found {len(issues)} issues")
        conn.commit()
        return {"issues": issues, "issue_count": len(issues)}

    # ── Backfill ─────────────────────────────────────────────────────

    def backfill_entities(self) -> dict:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT m.id, m.title, m.summary, m.workflow FROM memories m "
            "LEFT JOIN memory_entities me ON m.id = me.memory_id "
            "WHERE me.memory_id IS NULL"
        ).fetchall()

        backfilled = 0
        for r in rows:
            extracted = extract_entities(r["title"], r["summary"], r["workflow"])
            for ent in extracted:
                key = f"{ent['type']}:{ent['name']}"
                conn.execute(
                    "INSERT OR IGNORE INTO entities (key, name, type) VALUES (?, ?, ?)",
                    (key, ent["name"], ent["type"]),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO memory_entities (memory_id, entity_key) VALUES (?, ?)",
                    (r["id"], key),
                )
            if extracted:
                backfilled += 1

        conn.commit()
        return {"backfilled": backfilled, "total_checked": len(rows)}

    # ── Global (not available in local mode) ─────────────────────────

    def _no_global(self):
        return {"error": "Global operations require cloud mode. Run 'python3 cli.py claim YOUR_KEY' to connect."}

    def search_global(self, query: str, limit: int = 10) -> list[dict]:
        return self._no_global()

    def browse_global(self) -> dict:
        return self._no_global()

    def get_global_graph(self, limit: int = 500) -> dict:
        return self._no_global()

    def get_global_stats(self) -> dict:
        return self._no_global()

    def sync_memories(self, sanitized_memories: list[dict]) -> dict:
        return self._no_global()

    # ── Internal ─────────────────────────────────────────────────────

    def _log(self, conn, action: str, detail: str = "") -> str:
        log_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO log_entries (id, action, detail, timestamp) VALUES (?, ?, ?, ?)",
            (log_id, action, detail, _now()),
        )
        return log_id

    @staticmethod
    def _memory_row_to_dict(row) -> dict:
        d = {"id": row["id"], "title": row["title"], "summary": row["summary"], "project": row["project"], "created_at": row["created_at"]}
        try:
            d["tools_used"] = json.loads(row["tools_used"])
        except (KeyError, TypeError):
            pass
        return d
