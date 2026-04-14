---
name: hive-prune
description: Run health checks on the Hivemind knowledge graph and fix issues found.
disable-model-invocation: true
allowed-tools: Bash, Read, mcp__hivemind__lint_graph, mcp__hivemind__search_memories, mcp__hivemind__get_memory, mcp__hivemind__synthesize_topic, mcp__hivemind__update_synthesis_node, mcp__hivemind__find_synthesis_gaps, mcp__hivemind__view_log
---

# Hive-Prune: Knowledge Graph Health Check

You are running health checks on the Hivemind knowledge graph and taking corrective action for issues found.

## Step 1: Run the Lint Check

Call `lint_graph` to get the full health report. It checks for:

1. **Orphaned memories** — memories with no entity links
2. **Stale syntheses** — synthesis nodes out of sync with actual contributors
3. **Disconnected entities** — entities mentioned by only 1 memory
4. **Category imbalance** — oversized or singleton categories
5. **Knowledge gaps** — entity clusters with 3+ memories but no synthesis
6. **Potential duplicates** — memories with 80%+ entity overlap

## Step 2: Fix Orphaned Memories

For each orphaned memory (no entity links):

```bash
# Backfill entities for all orphaned memories
python3 "$HIVE_HOME/cli.py" backfill-entities
```

Where `$HIVE_HOME` is either `~/.claude/plugins/cache/hivemind` or `~/.claude/hivemind`.

## Step 3: Fix Knowledge Gaps

For each knowledge gap (entity with 3+ memories, no synthesis):
1. Read the contributing memories using `get_memory`
2. Write a synthesis that integrates their knowledge
3. Store with `synthesize_topic`

Follow the same synthesis writing guidelines as `/hive-myelinate`.

## Step 4: Fix Stale Syntheses

For each stale synthesis (memory_count mismatch):
1. Read the synthesis and its actual contributing memories
2. Update the summary to incorporate any new knowledge
3. Call `update_synthesis_node` with the refreshed content

## Step 5: Report Duplicates and Imbalances

For potential duplicates and category imbalances, report them to the user but don't auto-fix — these require human judgment:
- Duplicates might be intentionally separate memories covering different aspects
- Category imbalance might be natural (some topics have more activity)

## Step 6: Summary Report

Present a clear summary:
- Issues found (by type)
- Issues auto-fixed
- Issues requiring human review
- Overall graph health score (issues / total nodes)
