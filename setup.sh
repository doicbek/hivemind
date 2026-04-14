#!/bin/bash
# Hivemind - Plugin setup

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"

echo "=== Hivemind Setup ==="

# ── 1. Install Python dependencies ──────────────────────────────────
echo "Installing Python dependencies..."
pip3 install -q httpx mcp 2>/dev/null || pip install -q httpx mcp 2>/dev/null || {
    echo "WARNING: Could not install Python packages. Please run: pip3 install httpx mcp"
}

# ── 2. Register MCP server with Claude Code ─────────────────────────
echo "Registering Hivemind MCP server..."
if command -v claude &>/dev/null; then
    # Remove old registration if present, then add fresh
    claude mcp remove hivemind -s user 2>/dev/null || true
    claude mcp add hivemind -s user -- python3 "$SCRIPT_DIR/mcp_server.py"
    echo "MCP server registered globally (all sessions)."
else
    echo "WARNING: 'claude' CLI not found. Add the MCP server manually:"
    echo "  claude mcp add hivemind -s user -- python3 $SCRIPT_DIR/mcp_server.py"
fi

# ── 3. Install skills ───────────────────────────────────────────────
SKILLS_DIR="$HOME/.claude/skills"
mkdir -p "$SKILLS_DIR"
for skill in hive hive-myelinate hive-prune; do
    if [ -d "$SCRIPT_DIR/skills/$skill" ]; then
        rm -rf "$SKILLS_DIR/$skill"
        cp -r "$SCRIPT_DIR/skills/$skill" "$SKILLS_DIR/$skill"
    fi
done
echo "Skills installed: /hive, /hive-myelinate, /hive-prune"

# ── 4. Patch CLAUDE.md ──────────────────────────────────────────────
HIVEMIND_MARKER="get_memories_for_task"
HIVEMIND_BLOCK='# Hivemind — Memory-Augmented Sessions

When starting a non-trivial task (debugging, error recovery, architecture decisions), call `get_memories_for_task` with a short description of the problem. Past sessions may have captured relevant patterns, workflows, and solutions. Check before re-solving from scratch.

When encountering a specific error, call `search_memories` with the error type or key terms.'

if [ -f "$CLAUDE_MD" ]; then
    if ! grep -q "$HIVEMIND_MARKER" "$CLAUDE_MD"; then
        echo "" >> "$CLAUDE_MD"
        echo "$HIVEMIND_BLOCK" >> "$CLAUDE_MD"
        echo "Added Hivemind guidance to $CLAUDE_MD"
    else
        echo "Hivemind guidance already present in $CLAUDE_MD"
    fi
else
    mkdir -p "$HOME/.claude"
    echo "$HIVEMIND_BLOCK" > "$CLAUDE_MD"
    echo "Created $CLAUDE_MD with Hivemind guidance"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Hivemind will auto-provision your account on first use."
echo "Just start a new Claude Code session — no further setup needed."
echo ""
echo "Optional: visit the Hivemind web dashboard to claim your account"
echo "and access graph visualization."
