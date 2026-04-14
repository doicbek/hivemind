"""HTTP client for the Hivemind cloud API.

Thin client that mirrors memory_store operations over HTTP.
All requests are authenticated via API key stored in ~/.hivemind/config.json.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

import config

# Timeout for all requests (seconds)
TIMEOUT = 30.0


class HivemindClient:
    """HTTP client for the Hivemind cloud API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or config.get_api_key()
        self.base_url = (base_url or config.get_cloud_url()).rstrip("/")
        self._client = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=TIMEOUT,
            )
        return self._client

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def auto_provision(self) -> dict:
        """Auto-register anonymously and get an API key."""
        import platform
        import hashlib
        machine_id = hashlib.sha256(platform.node().encode()).hexdigest()[:24]
        resp = httpx.post(
            f"{self.base_url}/api/auth/auto-provision",
            json={"machine_id": machine_id},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        config.set_api_key(data["api_key"])
        self.api_key = data["api_key"]
        self._client = None  # force re-create with new auth header
        return data

    def ensure_provisioned(self):
        """Auto-provision if no API key exists."""
        if not self.api_key:
            self.auto_provision()

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an HTTP request and return the JSON response."""
        if not self.api_key:
            return {"error": "No API key configured. Run 'bash setup.sh' or: python3 cli.py auth set-key YOUR_API_KEY"}
        client = self._get_client()
        resp = client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, **params) -> dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, data: dict) -> dict:
        return self._request("POST", path, json=data)

    def _put(self, path: str, data: dict) -> dict:
        return self._request("PUT", path, json=data)

    def _delete(self, path: str) -> dict:
        return self._request("DELETE", path)

    # ── Auth ─────────────────────────────────────────────────────────

    def auth_status(self) -> dict:
        """Check authentication status and cloud connectivity."""
        return self._get("/api/auth/status")

    # ── Memories ─────────────────────────────────────────────────────

    def store_memory(
        self,
        title: str,
        summary: str,
        workflow: str,
        tools_used: list[str],
        categories: list[str],
        project: str,
        session_id: str,
        user_id: str | None = None,
    ) -> str:
        """Store a new memory. Returns memory ID."""
        result = self._post("/api/memories", {
            "title": title,
            "summary": summary,
            "workflow": workflow,
            "tools_used": tools_used,
            "categories": categories,
            "project": project,
            "session_id": session_id,
        })
        return result.get("id", "")

    def search_memories(self, query: str, limit: int = 5) -> list[dict]:
        """Full-text search on memories."""
        result = self._get("/api/memories/search", q=query, limit=limit)
        return result.get("results", [])

    def search_with_expansion(
        self, query: str, limit: int = 5, expansion_limit: int = 5
    ) -> dict:
        """Search with graph-based entity expansion."""
        return self._get(
            "/api/memories/search",
            q=query, limit=limit, expand=True, expansion_limit=expansion_limit,
        )

    def search_by_category(self, category: str, limit: int = 10) -> list[dict]:
        """Get memories in a category."""
        result = self._get(f"/api/categories/{category}/memories", limit=limit)
        return result.get("results", [])

    def get_memory(self, memory_id: str) -> dict | None:
        """Get full memory details."""
        result = self._get(f"/api/memories/{memory_id}")
        if "error" in result:
            return None
        return result.get("memory")

    def get_categories(self) -> list[dict]:
        """Return category tree."""
        result = self._get("/api/categories")
        return result.get("categories", [])

    # ── Synthesis ────────────────────────────────────────────────────

    def create_synthesis(
        self,
        topic: str,
        summary: str,
        key_findings: str,
        memory_ids: list[str],
        entity_keys: list[str] | None = None,
    ) -> str:
        """Create a synthesis node. Returns synthesis ID."""
        result = self._post("/api/syntheses", {
            "topic": topic,
            "summary": summary,
            "key_findings": key_findings,
            "memory_ids": memory_ids,
            "entity_keys": entity_keys or [],
        })
        return result.get("id", "")

    def update_synthesis(
        self,
        synthesis_id: str,
        summary: str | None = None,
        key_findings: str | None = None,
        add_memory_ids: list[str] | None = None,
    ) -> dict:
        """Update a synthesis node."""
        data = {}
        if summary is not None:
            data["summary"] = summary
        if key_findings is not None:
            data["key_findings"] = key_findings
        if add_memory_ids:
            data["add_memory_ids"] = add_memory_ids
        return self._put(f"/api/syntheses/{synthesis_id}", data)

    def get_synthesis(self, synthesis_id: str) -> dict | None:
        """Get full synthesis details."""
        result = self._get(f"/api/syntheses/{synthesis_id}")
        if "error" in result:
            return None
        return result.get("synthesis")

    def list_syntheses(self, limit: int = 20) -> list[dict]:
        """List synthesis nodes."""
        result = self._get("/api/syntheses", limit=limit)
        return result.get("syntheses", [])

    def find_synthesis_gaps(self, min_memories: int = 3) -> list[dict]:
        """Find entity clusters lacking synthesis."""
        result = self._get("/api/syntheses/gaps", min_memories=min_memories)
        return result.get("gaps", [])

    # ── Graph + Stats ────────────────────────────────────────────────

    def get_graph_data(self, node_types: list[str] | None = None, limit: int = 500) -> dict:
        """Get graph data for visualization."""
        params = {"limit": limit}
        if node_types:
            params["types"] = ",".join(node_types)
        return self._get("/api/graph", **params)

    def get_stats(self) -> dict:
        """Get node counts and top entities."""
        return self._get("/api/stats")

    # ── Log ──────────────────────────────────────────────────────────

    def get_log(self, limit: int = 20, action_filter: str | None = None) -> list[dict]:
        """Get activity log entries."""
        params = {"limit": limit}
        if action_filter:
            params["action"] = action_filter
        result = self._get("/api/log", **params)
        return result.get("entries", [])

    def append_log(self, action: str, detail: str = "") -> str:
        """Append a log entry. Returns log ID."""
        result = self._post("/api/log", {"action": action, "detail": detail})
        return result.get("id", "")

    # ── Lint ─────────────────────────────────────────────────────────

    def lint(self) -> dict:
        """Run graph health checks."""
        return self._get("/api/lint")

    # ── Backfill ─────────────────────────────────────────────────────

    def backfill_entities(self) -> dict:
        """Trigger entity backfill on the server."""
        return self._post("/api/memories/backfill-entities", {})

    # ── Global Graph ─────────────────────────────────────────────────

    def search_global(self, query: str, limit: int = 10) -> list[dict]:
        """Search the global (sanitized) knowledge graph."""
        result = self._get("/api/global/search", q=query, limit=limit)
        return result.get("results", [])

    def browse_global(self) -> dict:
        """Browse global categories."""
        return self._get("/api/global/categories")

    def get_global_graph(self, limit: int = 500) -> dict:
        """Get global graph data for visualization."""
        return self._get("/api/global/graph", limit=limit)

    def get_global_stats(self) -> dict:
        """Get global graph statistics."""
        return self._get("/api/global/stats")

    # ── Sync ─────────────────────────────────────────────────────────

    def sync_memories(self, sanitized_memories: list[dict]) -> dict:
        """Push sanitized memories to the global graph.

        Args:
            sanitized_memories: List of memory dicts already run through sanitizer
        """
        return self._post("/api/sync/memories", {"memories": sanitized_memories})


# Module-level convenience instance
_client = None


def get_client():
    """Get or create the module-level client instance.

    Returns LocalClient in local mode, HivemindClient in cloud mode.
    """
    global _client
    if _client is None:
        if config.get_mode() == "local":
            from local_client import LocalClient
            _client = LocalClient()
        else:
            _client = HivemindClient()
    return _client


def close():
    """Close the module-level client."""
    global _client
    if _client:
        _client.close()
        _client = None
