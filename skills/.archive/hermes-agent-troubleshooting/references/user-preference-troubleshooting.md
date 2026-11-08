# User Preference: Concise Troubleshooting

## Summary
The user prefers direct, actionable troubleshooting steps with minimal explanation. They want to see the actual commands and results rather than process descriptions.

## Key Details
- When troubleshooting network issues, they want direct commands to execute without meta-commentary
- They prefer actionable output over process documentation
- They dislike verbose explanations when they just want to fix something

## Implications for Troubleshooting
When applying troubleshooting workflows:
1. **Prioritize commands over descriptions**: Provide the exact shell commands to run
2. **Skip process rationale**: Don't explain "why" these steps are needed unless requested
3. **Focus on results**: Show what the commands return, not just the steps

## Examples of Preference Alignment
**Before (verbose):**
```
To fix this networking issue, we need to check the service logs first. Then we'll look at how Tailscale is configured, and finally run a command to reconfigure the gateway binding.
```

**After (concise):**
```bash
# Expose localhost-bound gateway to tailnet (HTTPS by default)
tailscale serve --bg 8642

# Verify - should return HTTP 200
curl -sk -H "Authorization: Bearer $API_SERVER_KEY" https://studio.taile85139.ts.net/v1/models
```

This approach aligns with the user's stated preference for "short, direct, actionable" responses when troubleshooting technical issues.