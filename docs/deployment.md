# Deployment

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
docker build -f docker/Dockerfile -t knucklessg1/salesforce-agent:latest .
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
salesforce-mcp.arpa {
    reverse_proxy salesforce-agent-mcp:8000
}
```

Point an `A` record for `salesforce-mcp.arpa` at the ingress node in
Technitium, then use `https://salesforce-mcp.arpa/mcp` as the client `MCP_URL`
and `https://salesforce-mcp.arpa/health` as the health-check target.
