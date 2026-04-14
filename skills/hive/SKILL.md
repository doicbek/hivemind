---
name: hive
description: Review the current session and extract interesting problem-solving patterns, storing them as memories.
disable-model-invocation: true
allowed-tools: Read, Bash, Grep, Glob, mcp__hivemind__store_memory, mcp__hivemind__browse_categories, mcp__hivemind__search_memories
---

# Hive: Session Memory Extraction

You are reviewing the current Claude Code session to extract valuable problem-solving patterns and store them as structured memories. Future sessions will be able to query these memories via MCP.

## Step 1: Find the Session Transcript

The current session's transcript is a JSONL file. Find it:

```bash
# List recent transcripts for this project, sorted by modification time
ls -lt ~/.claude/projects/*/?.jsonl 2>/dev/null | head -5
```

Look for the most recently modified `.jsonl` file in `~/.claude/projects/`. The project directory name is derived from the working directory path with `/` replaced by `-`.

Read the transcript file. If it's very large, read it in chunks (e.g., first 500 lines, then next 500, etc.).

## Step 2: Query Existing Categories

Before categorizing memories, see what categories already exist:

Call `browse_categories` via MCP to see the full category tree.

Use existing categories when they fit. Only create new ones when the pattern genuinely doesn't fit existing categories.

## Step 3: Analyze the Transcript

Look through the session for interesting patterns. Focus on:

1. **Error Recovery Workflows** - When something failed and was successfully recovered
   - Build failures diagnosed and fixed
   - Runtime errors traced to root cause
   - Configuration issues resolved

2. **Creative Problem-Solving** - Non-obvious approaches that worked
   - Workarounds for tool limitations
   - Clever use of available tools
   - Unconventional debugging strategies

3. **Tool Usage Patterns** - Effective tool combinations or usage
   - Which tools were used together effectively
   - Tool parameters that proved useful
   - Multi-step tool workflows

4. **Debugging Strategies** - Systematic debugging approaches
   - How errors were diagnosed
   - Which investigation steps led to the answer
   - Red herrings that were avoided or caught

5. **Architectural Decisions** - Design choices and their rationale
   - Why one approach was chosen over another
   - Trade-offs that were considered
   - Patterns that were applied

**Skip mundane patterns** like simple file reads, basic git operations, or straightforward edits that don't involve interesting problem-solving.

## Step 4: Extract and Store Memories

For each interesting pattern found, store it directly using the `store_memory` MCP tool:

- **title**: Short descriptive title (e.g., "Fix Python import cycle by lazy-loading module")
- **summary**: 2-3 sentences capturing the essence — problem, approach, outcome
- **workflow**: Step-by-step what was done, including tools and key commands
- **tools_used**: List of Claude Code tools (e.g., ["Grep", "Edit", "Bash"])
- **categories**: Hierarchical categories in kebab-case (e.g., ["debugging", "debugging/import-errors"])
- **project**: The working directory path
- **session_id**: The session transcript filename

Memories are automatically synced to the global knowledge graph (sanitized — file paths and repo names are censored).

## Step 5: Update Syntheses

After storing memories, check if any existing synthesis pages should be updated:

1. For each stored memory, check if it shares entities with existing syntheses by searching for the memory's key terms
2. If related syntheses exist, note them in your report so the user can run `/hive-myelinate` to update them
3. If you stored 3+ memories on a shared topic (same entities), note this as a synthesis gap

This step is informational — actual synthesis creation is handled by `/hive-myelinate`.

## Step 6: Report Results

After storing all memories, summarize what was captured:

- Number of memories stored
- Categories used (new and existing)
- Brief title of each memory

Format as a clean summary the user can review.

## Guidelines

- **Quality over quantity**: 2-3 excellent memories are better than 10 mediocre ones
- **Be specific**: Include actual error messages, file paths, and tool parameters when relevant
- **Think about retrieval**: Write titles and summaries that will match well when future sessions search for similar problems
- **Respect hierarchy**: Use parent/child categories (e.g., `debugging/neo4j-errors`) to keep the graph organized
- **Include the "why"**: Don't just describe what happened — capture why the approach worked
- **Session context**: Include the session_id and project path so memories can be traced back to their source
