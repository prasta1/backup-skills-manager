# System Prompt Optimization in Distributed Inference

## Problem
In distributed inference setups (e.g., Mac Studio as primary with local fallback), the system prompt can grow significantly due to:
- Tool lists and guidance blocks being duplicated across all instances
- Memory/user profile blocks that get fully expanded in each prompt
- Context files like AGENTS.md being included in every session

## Impact on Performance
When running distributed inference with multiple Hermes instances:
1. **Token Usage**: Large prompts increase token costs and may hit context window limits
2. **Latency**: Larger prompts increase inference time, especially for long-running sessions
3. **Resource Consumption**: More memory and compute required for prompt processing

## Optimization Strategies

### 1. Profile-Specific Configuration
Use profile-specific config to reduce redundant tool inclusion:
```yaml
# In ~/.hermes/profiles/<profile>/config.yaml
providers:
  lmstudio-studio:
    base_url: http://studio.taile85139.ts.net:1234/v1
    default_model: nousresearch/hermes-4-70b
    fallback_to: lmstudio-local

  lmstudio-local:
    base_url: http://localhost:1234/v1
    default_model: google/gemma-4-26b-a4b-qat
```

### 2. Prompt Compression for Remote Instances
Implement system prompt compression:
- Use shorter tool lists on local fallback instances
- Skip memory/user profile expansion when not needed for the specific task
- Apply context file truncation on lighter instances

### 3. Centralized Memory Management
Consider centralized memory storage:
- Avoid full profile expansion in fallback instances
- Use lightweight summary blocks instead of full memory dumps

## Best Practices for Distributed Systems

1. **Token Efficiency**: Keep system prompts under 10k chars where possible, especially on local fallbacks
2. **Task-Aware Prompting**: Only include tools and guidance relevant to the specific task at hand
3. **Profile Optimization**: Configure each profile with minimal necessary tools and guidance blocks
4. **Performance Monitoring**: Track prompt size impacts across distributed instances to identify bottlenecks

## Example Implementation
For local fallback instances, reduce prompt size by:
- Removing full skill documentation from stable tier
- Using abbreviated tool lists in context tier  
- Applying memory/user profile compression strategies