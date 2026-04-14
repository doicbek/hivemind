"""Fast regex/keyword entity extraction from memory text.

Extracts entities (libraries, error types, tools, languages, frameworks,
concepts) without LLM calls for use in KG-style cross-memory linking.
"""

import re

# Claude Code tool names
TOOLS = {
    "read", "edit", "write", "bash", "grep", "glob", "agent",
    "webfetch", "websearch", "notebook", "notebookedit", "taskwrite",
    "todoread", "todowrite", "mcp",
}

LANGUAGES = {
    "python", "javascript", "typescript", "rust", "go", "java", "c++",
    "c#", "ruby", "php", "swift", "kotlin", "scala", "haskell",
    "elixir", "erlang", "lua", "perl", "r", "julia", "dart", "zig",
    "ocaml", "clojure", "shell", "bash", "zsh", "sql", "html", "css",
    "yaml", "json", "toml", "xml", "graphql", "protobuf",
}

FRAMEWORKS = {
    "react", "next.js", "nextjs", "vue", "angular", "svelte", "fastapi",
    "flask", "django", "express", "nestjs", "spring", "rails",
    "laravel", "phoenix", "actix", "axum", "gin", "echo", "fiber",
    "tailwind", "bootstrap", "material-ui", "mui", "chakra",
    "prisma", "sqlalchemy", "typeorm", "sequelize", "mongoose",
    "pytest", "jest", "vitest", "mocha", "cypress", "playwright",
    "webpack", "vite", "rollup", "esbuild", "turbopack",
    "docker", "kubernetes", "k8s", "terraform", "ansible",
    "neo4j", "redis", "postgres", "postgresql", "mongodb", "mysql",
    "sqlite", "elasticsearch", "kafka", "rabbitmq", "celery",
    "graphql", "grpc", "rest", "websocket",
    "langchain", "llamaindex", "pytorch", "tensorflow", "numpy", "pandas",
    "scipy", "scikit-learn", "sklearn", "huggingface", "transformers",
    "openai", "anthropic", "claude", "gpt",
}

CONCEPTS = {
    "circular import": "circular-import",
    "race condition": "race-condition",
    "deadlock": "deadlock",
    "lazy loading": "lazy-loading",
    "eager loading": "eager-loading",
    "dependency injection": "dependency-injection",
    "memory leak": "memory-leak",
    "stack overflow": "stack-overflow",
    "buffer overflow": "buffer-overflow",
    "null pointer": "null-pointer",
    "type error": "type-error",
    "segfault": "segfault",
    "segmentation fault": "segfault",
    "connection pool": "connection-pool",
    "connection timeout": "connection-timeout",
    "rate limit": "rate-limit",
    "retry logic": "retry-logic",
    "backoff": "backoff",
    "exponential backoff": "exponential-backoff",
    "caching": "caching",
    "memoization": "memoization",
    "serialization": "serialization",
    "deserialization": "deserialization",
    "marshalling": "marshalling",
    "middleware": "middleware",
    "authentication": "authentication",
    "authorization": "authorization",
    "cors": "cors",
    "csrf": "csrf",
    "xss": "xss",
    "sql injection": "sql-injection",
    "migration": "migration",
    "schema migration": "schema-migration",
    "hot reload": "hot-reload",
    "code splitting": "code-splitting",
    "tree shaking": "tree-shaking",
    "bundling": "bundling",
    "minification": "minification",
    "transpilation": "transpilation",
    "polyfill": "polyfill",
    "monorepo": "monorepo",
    "microservice": "microservice",
    "event sourcing": "event-sourcing",
    "pub sub": "pub-sub",
    "message queue": "message-queue",
    "load balancing": "load-balancing",
    "sharding": "sharding",
    "replication": "replication",
    "index": "indexing",
    "full text search": "full-text-search",
    "graph traversal": "graph-traversal",
    "breadth first search": "bfs",
    "depth first search": "dfs",
    "recursion": "recursion",
    "memoize": "memoization",
    "decorator": "decorator",
    "metaclass": "metaclass",
    "generator": "generator",
    "async await": "async-await",
    "promise": "promise",
    "callback": "callback",
    "observable": "observable",
    "state management": "state-management",
    "virtual dom": "virtual-dom",
    "server side rendering": "server-side-rendering",
    "ssr": "server-side-rendering",
    "static site generation": "static-site-generation",
    "ssg": "static-site-generation",
    "continuous integration": "ci",
    "continuous deployment": "cd",
    "ci cd": "ci-cd",
    "unit test": "unit-test",
    "integration test": "integration-test",
    "end to end test": "e2e-test",
    "e2e test": "e2e-test",
    "mock": "mocking",
    "stub": "stubbing",
    "fixture": "fixture",
    "refactor": "refactoring",
    "technical debt": "tech-debt",
    "code review": "code-review",
    "pull request": "pull-request",
    "merge conflict": "merge-conflict",
    "rebase": "rebase",
    "cherry pick": "cherry-pick",
    "environment variable": "env-vars",
    "env var": "env-vars",
    "dotenv": "dotenv",
    "singleton": "singleton",
    "factory pattern": "factory-pattern",
    "observer pattern": "observer-pattern",
    "strategy pattern": "strategy-pattern",
    "adapter pattern": "adapter-pattern",
}

# Regex for error/exception class names
_ERROR_RE = re.compile(r"\b([A-Z][a-zA-Z]*(?:Error|Exception|Failure|Fault))\b")

# Regex for Python import patterns
_IMPORT_RE = re.compile(
    r"(?:^|\n)\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))"
)

# Common libraries that might appear as plain text references
LIBRARIES = {
    "numpy", "pandas", "scipy", "matplotlib", "seaborn", "plotly",
    "requests", "httpx", "aiohttp", "urllib", "beautifulsoup", "scrapy",
    "pydantic", "marshmallow", "attrs", "dataclasses",
    "asyncio", "threading", "multiprocessing", "concurrent",
    "logging", "structlog", "loguru",
    "click", "typer", "argparse", "fire",
    "boto3", "gcloud", "azure",
    "jwt", "bcrypt", "cryptography", "passlib",
    "celery", "rq", "dramatiq", "huey",
    "alembic", "flyway", "liquibase",
    "pip", "poetry", "pipenv", "conda",
    "npm", "yarn", "pnpm", "bun", "deno",
    "git", "github", "gitlab", "bitbucket",
    "nginx", "apache", "caddy", "traefik",
    "gunicorn", "uvicorn", "hypercorn", "daphne",
    "supervisor", "systemd", "pm2",
    "grafana", "prometheus", "datadog", "sentry",
    "neo4j", "arangodb", "dgraph", "tigergraph",
}


def extract_entities(title, summary, workflow):
    """Extract entities from memory text fields.

    Returns list of {"name": str, "type": str} dicts.
    """
    text = f"{title}\n{summary}\n{workflow}".lower()
    text_original = f"{title}\n{summary}\n{workflow}"
    seen = set()
    entities = []

    def _add(name, entity_type):
        key = (name.lower(), entity_type)
        if key not in seen:
            seen.add(key)
            entities.append({"name": name.lower(), "type": entity_type})

    # Error types (preserve original case)
    for match in _ERROR_RE.finditer(text_original):
        _add(match.group(1), "error-type")

    # Python imports
    for match in _IMPORT_RE.finditer(text_original):
        lib = (match.group(1) or match.group(2)).split(".")[0]
        _add(lib, "library")

    # Tool mentions
    for tool in TOOLS:
        if re.search(r"\b" + re.escape(tool) + r"\b", text):
            _add(tool, "tool")

    # Language mentions
    for lang in LANGUAGES:
        pattern = r"\b" + re.escape(lang) + r"\b"
        if re.search(pattern, text):
            _add(lang, "language")

    # Framework mentions
    for fw in FRAMEWORKS:
        pattern = r"\b" + re.escape(fw) + r"\b"
        if re.search(pattern, text):
            _add(fw, "framework")

    # Library mentions
    for lib in LIBRARIES:
        pattern = r"\b" + re.escape(lib) + r"\b"
        if re.search(pattern, text):
            _add(lib, "library")

    # Concept mentions
    for phrase, canonical in CONCEPTS.items():
        if phrase in text:
            _add(canonical, "concept")

    return entities
