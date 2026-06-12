# Deployment

<!-- BEGIN GENERATED: deployment-options -->
## Deployment Options

`salesforce-agent` exposes its MCP server (console script `salesforce-mcp`) four ways. Pick the row that
matches where the server runs relative to your MCP client, then copy the matching
`mcp_config.json` below. Replace the `<your-…>` placeholders with the values from the **Configuration / Environment Variables** section.

| # | Option | Transport | Where it runs | `mcp_config.json` key |
|---|--------|-----------|---------------|------------------------|
| 1 | stdio | `stdio` | client launches a subprocess | `command` |
| 2 | Streamable-HTTP (local) | `streamable-http` | a local network port | `command` or `url` |
| 3 | Local container / uv | `stdio` or `streamable-http` | Docker / Podman / uv on this host | `command` or `url` |
| 4 | Remote URL | `streamable-http` | a remote host behind Caddy | `url` |

### 1. stdio (local subprocess)

The client launches the server over stdio via `uvx` — best for local IDEs
(Cursor, Claude Desktop, VS Code):

```json
{
  "mcpServers": {
    "salesforce-mcp": {
      "command": "uvx",
      "args": ["--from", "salesforce-agent", "salesforce-mcp"],
      "env": {
        "SALESFORCE_INSTANCE_URL": "<your-salesforce_instance_url>",
        "SALESFORCE_LOGIN_URL": "<your-salesforce_login_url>",
        "SALESFORCE_REFRESH_TOKEN": "<your-salesforce_refresh_token>"
      }
    }
  }
}
```

### 2. Streamable-HTTP (local process)

Run the server as a long-lived HTTP process:

```bash
uvx --from salesforce-agent salesforce-mcp --transport streamable-http --host 0.0.0.0 --port 8000
curl -s http://localhost:8000/health        # {"status":"OK"}
```

Then either let the client launch it:

```json
{
  "mcpServers": {
    "salesforce-mcp": {
      "command": "uvx",
      "args": ["--from", "salesforce-agent", "salesforce-mcp", "--transport", "streamable-http", "--port", "8000"],
      "env": {
        "TRANSPORT": "streamable-http",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "SALESFORCE_INSTANCE_URL": "<your-salesforce_instance_url>",
        "SALESFORCE_LOGIN_URL": "<your-salesforce_login_url>",
        "SALESFORCE_REFRESH_TOKEN": "<your-salesforce_refresh_token>"
      }
    }
  }
}
```

…or connect to the already-running process by URL:

```json
{
  "mcpServers": {
    "salesforce-mcp": { "url": "http://localhost:8000/mcp" }
  }
}
```

### 3. Local container / uv

**(a) Launch a container directly from `mcp_config.json`** (stdio over the container —
no ports to manage). Swap `docker` for `podman` for a daemonless runtime:

```json
{
  "mcpServers": {
    "salesforce-mcp": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TRANSPORT=stdio",
        "-e", "SALESFORCE_INSTANCE_URL=<your-salesforce_instance_url>",
        "-e", "SALESFORCE_LOGIN_URL=<your-salesforce_login_url>",
        "-e", "SALESFORCE_REFRESH_TOKEN=<your-salesforce_refresh_token>",
        "knucklessg1/salesforce-agent:latest"
      ]
    }
  }
}
```

**(b) Run a local streamable-http container, then connect by URL:**

```bash
docker run -d --name salesforce-mcp -p 8000:8000 \
  -e TRANSPORT=streamable-http \
  -e PORT=8000 \
  -e SALESFORCE_INSTANCE_URL="<your-salesforce_instance_url>" \
  -e SALESFORCE_LOGIN_URL="<your-salesforce_login_url>" \
  -e SALESFORCE_REFRESH_TOKEN="<your-salesforce_refresh_token>" \
  knucklessg1/salesforce-agent:latest
# or, from a clone of this repo:
docker compose -f docker/mcp.compose.yml up -d
```

```json
{
  "mcpServers": {
    "salesforce-mcp": { "url": "http://localhost:8000/mcp" }
  }
}
```

**(c) From a local checkout with `uv`:**

```bash
uv run salesforce-mcp --transport streamable-http --port 8000
```

### 4. Remote URL (deployed behind Caddy)

When the server is deployed remotely (e.g. as a Docker service) and published through
Caddy on the internal `*.arpa` zone, connect with the `"url"` key — no local process or
image required:

```json
{
  "mcpServers": {
    "salesforce-mcp": { "url": "http://salesforce-mcp.arpa/mcp" }
  }
}
```

Caddy reverse-proxies `http://salesforce-mcp.arpa` to the container's `:8000`
streamable-http listener; `http://salesforce-mcp.arpa/health` returns
`{"status":"OK"}` when the service is live.
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
