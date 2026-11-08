# System Prompt Optimization in Hermes

## Problem
The system prompt in Hermes can grow to over 32k characters due to:
- Repeated injection of the same content (e.g., Hermes self-documentation, tool lists)
- Expansion of context files like AGENTS.md
- Memory/user profile blocks that get fully expanded
- Tool-use enforcement and guidance blocks

## Root Causes
1. **Over-inclusion of meta-documentation**: The system prompt includes full copies of skill documentation, tool lists, and internal guidelines that repeat across conversations
2. **Lack of deduplication logic**: Content that should only appear once (like tool availability) is repeated in each prompt tier
3. **Context file expansion**: Project context files (e.g., AGENTS.md) are fully included when they should be minimal or skipped

## Solution Approaches
1. **Prompt tier consolidation**: Merge redundant content from stable and context tiers into a single canonical source
2. **Conditional content injection**: Only include tool-specific guidance when relevant tools are present
3. **Template-based system**: Use parameterized templates to avoid repeating full documentation blocks
4. **Memory/user block compression**: Truncate or reference external sources instead of full expansion

## Performance Impact
Reducing system prompt size from 32k+ to 10k chars can:
- Improve inference latency by reducing context window pressure
- Decrease token costs for long conversations
- Prevent hitting model-specific context limits (e.g., 128k token limit)
- Improve cache efficiency for long-running sessions

## Best Practices
- Keep system prompt under 10k chars where possible
- Prioritize identity and core task instructions over tool lists
- Use memory/user profiles as lightweight summaries, not full dumps
- Implement content deduplication for repeated blocks like platform hints or tool guidance