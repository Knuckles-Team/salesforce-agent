# Deployment

<!-- BEGIN GENERATED: deployment-options -->
## Deployment Options

`salesforce-agent` supports local stdio, a loopback-only development listener, a
least-privilege stdio container, and a remote authenticated HTTPS boundary.
Provider endpoint, credential, selector, identity, and trust material are supplied
at runtime through `AgentConfig`; none is stored in this repository.

### Installed stdio process

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "salesforce-mcp",
      "args": [],
      "env": {"MCP_TOOL_MODE": "intent"}
    }
  }
}
```

### Loopback development listener

```bash
salesforce-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

Do not expose this listener beyond loopback. Network deployments require direct TLS
or an explicitly trusted TLS-terminating ingress, configured authentication, exact
`MCP_ALLOWED_HOSTS`, and an exact trusted-proxy CIDR policy.

### Least-privilege local container

```bash
docker run -i --rm \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit=256 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  -e TRANSPORT=stdio \
  registry.example.invalid/salesforce-agent@sha256:<digest> salesforce-mcp
```

The operator projects the selected AgentConfig profile into the process at runtime;
the image remains immutable and contains no environment connection profile.

### Remote authenticated HTTPS endpoint

```json
{
  "mcpServers": {
    "salesforce": {"url": "https://service.example.invalid/mcp"}
  }
}
```

Store the real remote URL, outbound identity reference, and TLS-profile reference in
`AgentConfig`, not in MCP client JSON or documentation.
<!-- END GENERATED: deployment-options -->

## MCP server transports

=== "stdio (default)"

    ```bash
    salesforce-mcp
    ```

    For local agent integration — the MCP client owns the process and speaks
    JSON-RPC over stdin/stdout.

=== "streamable-http"

    ```bash
    salesforce-mcp --transport streamable-http --host 0.0.0.0 --port 8000
    ```

    For networked deployments behind a reverse proxy. The server exposes
    `/mcp` for clients and `/health` for orchestrator checks.

=== "sse"

    ```bash
    salesforce-mcp --transport sse --host 0.0.0.0 --port 8000
    ```

    Server-sent-events transport for clients that require it.

### Health check

```bash
curl -fsS http://localhost:8000/health
# {"status": "OK"}
```

## Docker Compose (MCP only)

```bash
cp .env.example .env   # fill in one auth flow
docker compose -f docker/mcp.compose.yml up -d
```

The MCP server listens on port `8000` (streamable-http) with a `/health` check.

## Docker Compose (MCP + Agent)

```bash
docker compose -f docker/agent.compose.yml up -d
```

This brings up both the `salesforce-agent-mcp` service (port 8000) and the
`salesforce-agent-agent` A2A service (port 9020, AG-UI web interface).

## Building the image

```bash
docker build -f docker/Dockerfile -t example/salesforce-agent:agent-local .
```

A `docker/debug.Dockerfile` is provided for an in-place editable install with
shell tooling and the Starship prompt.

## A2A agent server

```bash
salesforce-agent                  # standalone A2A server
```

The agent connects to the MCP server via `MCP_URL`
(`http://salesforce-agent-mcp:8000/mcp` in Compose) and exposes the A2A
endpoint and AG-UI web interface on its port.

## Environment

All configuration is via `SALESFORCE_*` environment variables — see
`.env.example`. Mount secrets (client secret, JWT private key) from your
secret store; never bake them into the image. Keep
`SALESFORCE_ALLOW_DESTRUCTIVE=False` in shared deployments. Per-domain tool
toggles (`SOQLTOOL`, `RECORDSTOOL`, `DESCRIBETOOL`, `BULKTOOL`, `ADMINTOOL`)
control which tools are registered.

## MCP client wiring

`mcp_config.json` at the repo root is the reference client entry
(`uv run salesforce-mcp` plus the full environment block).

## Reverse proxy + DNS (Caddy + Technitium)

For fleet deployments, publish the MCP server behind Caddy and register the
hostname in Technitium DNS:

```caddyfile
salesforce-mcp.example.invalid {
    reverse_proxy salesforce-agent-mcp:8000
}
```

Point an `A` record for `salesforce-mcp.example.invalid` at the ingress node in
Technitium, then use `https://salesforce-mcp.example.invalid/mcp` as the client `MCP_URL`
and `https://salesforce-mcp.example.invalid/health` as the health-check target.
