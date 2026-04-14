---
name: hive-myelinate
description: Find knowledge gaps in the memory graph and create synthesis pages that aggregate knowledge across memories.
disable-model-invocation: true
allowed-tools: Bash, Read, mcp__hivemind__find_synthesis_gaps, mcp__hivemind__get_memory, mcp__hivemind__synthesize_topic, mcp__hivemind__list_syntheses, mcp__hivemind__update_synthesis_node, mcp__hivemind__search_with_expansion
---

# Hive-Myelinate: Knowledge Compounding

You are creating synthesis pages — living summary documents that aggregate knowledge across multiple memories on a shared topic. This is the wiki layer that makes knowledge compound over time.

## Step 1: Find Knowledge Gaps

Call `find_synthesis_gaps` to identify entity clusters that have 3+ memories but no synthesis page yet.

Also call `list_syntheses` to see what synthesis pages already exist, so you can update stale ones if needed.

## Step 2: For Each Gap, Gather Contributing Memories

For each knowledge gap found:

1. Use the `memory_ids` returned in the gap result
2. Call `get_memory` for each memory ID to read its full content (title, summary, workflow)
3. Understand the common thread — what entity or concept connects these memories?

## Step 3: Write the Synthesis

For each gap, write a synthesis that:

- **Topic**: A descriptive topic name (e.g., "Neo4j Connection Patterns", "Python Import Error Recovery")
- **Summary**: A multi-paragraph synthesis that integrates knowledge from all contributing memories. Don't just list them — find patterns, contradictions, and insights across them. What does the collective knowledge teach?
- **Key Findings**: Bullet-point actionable takeaways. What should someone know if they encounter this topic?

## Step 4: Store the Synthesis

Call `synthesize_topic` with:
- `topic`: The topic name
- `summary`: Your synthesized summary
- `key_findings`: The bullet-point findings
- `memory_ids`: All contributing memory UUIDs
- `entity_keys`: The entity keys this synthesis covers (format: `type:name`)

## Step 5: Check for Stale Syntheses

If `list_syntheses` showed existing syntheses, check if any have new contributing memories that haven't been integrated. Use `search_with_expansion` to find memories related to existing synthesis topics.

If new memories are found, call `update_synthesis_node` to refresh the synthesis with updated content.

## Step 6: Report Results

Summarize:
- Number of new synthesis pages created
- Number of existing syntheses updated
- Topics covered
- Total memories aggregated

## Guidelines

- **Synthesize, don't summarize**: The value is in finding connections and patterns across memories, not listing them
- **Be specific**: Include concrete examples, error messages, and tool workflows from the contributing memories
- **Flag contradictions**: If memories disagree on an approach, note both perspectives and when each applies
- **Think about retrieval**: Write topics and summaries that will match well when future sessions search
- **Quality over quantity**: One excellent synthesis is better than five shallow ones
