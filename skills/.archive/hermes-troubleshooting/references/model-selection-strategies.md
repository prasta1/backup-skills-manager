# Model Selection Strategies

## Size vs Performance Tradeoffs

### Small Models (1-2B)
- **Pros**: Instant loading, ultra-low memory, free tokens
- **Cons**: Limited reasoning, poor at complex tasks
- **Best for**: Title generation, approval scoring, simple tool routing, profile descriptions

### Medium Models (7-9B)
- **Pros**: Good balance of quality/speed, reasonable memory (~5-6GB GGUF Q4)
- **Cons**: Not state-of-the-art on complex benchmarks
- **Best for**: Context compression, web summarization, triage/specifier tasks, curator reviews

### Large Models (24-30B)
- **Pros**: Strong reasoning, coding ability, better instruction following
- **Cons**: Higher memory usage, slower inference
- **Best for**: Main agent model, session search, complex decomposition

## Hermes Specific Recommendations

### GGUF Quantization Levels
- **Q4_K_M**: Best general purpose (fast, small, decent quality)
- **Q5_K_M**: Better quality, slightly larger
- **Q8_0**: Near-original quality, large files
- **MLX variants**: Fastest on Apple Silicon (M1/M2/M3)

### Model Sources

| Source | Format | Notes |
|--------|--------|-------|
| Ollama | Native | Easiest for OpenAI-compatible API |
| HuggingFace GGUF | GGUF | For LM Studio/llama.cpp |
| mlx-community | MLX | Apple Silicon optimized |

### Auxiliary Model Rationale

The key insight: **auxiliary tasks don't need the same model as your main agent.**

| Task | Reasoning Required | Token Savings | Recommendation |
|------|------------------|---------------|----------------|
| Title Generation | Minimal | ~95% | 1.7B model |
| Vision | Moderate | ~90% | 4B vision model |
| Compression | Low-Med | ~50% | 7-8B model |
| Web Extract | Low-Med | ~50% | 7-8B model |
| Approval | Minimal | ~95% | 1.7B model |
| MCP Routing | Minimal | ~90% | 1.7B model |
| Session Search | High | 0% | Keep main model |
| Curator | Med | ~75% | 8B model |
| Triage/Kanban | Med | ~75% | 8B model |