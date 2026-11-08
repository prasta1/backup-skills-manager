# Amplitude MCP Setup Notes

## Key Learnings from Session

### Authentication Method
- The Amplitude MCP server at `https://mcp.amplitude.com/mcp` uses **OAuth 2.0 only**
- It does **not** accept raw API keys or secrets as Bearer tokens
- Attempting to use API key/secret as Bearer token results in `401 invalid_token: Token is not active`
- Basic Auth (API key:secret) results in `401 Invalid authorization header format. Expected Bearer token`

### Correct Configuration Approach
When using `hermes mcp add` with the Amplitude MCP server:
1. Do **not** provide API key or secret during the add process
2. Let the `mcp-remote` package handle OAuth flow automatically
3. The server will prompt for authentication via browser when first launched

### Configuration That Works
```yaml
mcp:
  servers:
    - name: amplitude
      command: npx
      args:
        - mcp-remote
        - https://mcp.amplitude.com/mcp
```

### Troubleshooting Notes
1. **npx PATH issues in headless environments**: 
   - If you see "npx: command not found", find the absolute path with `command -v npx`
   - Update the config to use the full path: `/path/to/npx`

2. **OAuth Flow**:
   - On first launch, `mcp-remote` will print an authorization URL
   - This URL must be visited in a browser to complete authentication
   - After successful auth, the connection will be established

3. **Verification**:
   - After auth completes, use `hermes mcp list` to confirm server is enabled
   - Use `hermes mcp discover` to list available Amplitude tools
   - Expected tools include event export, segmentation, and other Amplitude APIs

### Session-Specific Details
- User's Amplitude credentials (API key/secret) are NOT used for MCP auth
- The MCP server handles its own OAuth flow with Amplitude backend
- No token storage needed in Hermes config for this specific MCP server

## Additional Context on OAuth Flow
The `mcp-remote` package sets up a local OAuth callback server (on port 20319) that captures the authorization code from Amplitude's OAuth endpoint and exchanges it for an access token. This process is handled automatically by the `mcp-remote` tool, but requires a web browser to complete the authentication.

If you're working in an environment where you cannot open a browser (like a remote server or CI pipeline), you'll need to set up an alternative authentication method, as the OAuth flow requires interactive browser access.

The `npx` command must be available in your PATH. If it's not found, you can locate it with `which npx` or `command -v npx` and use the full path in your config.