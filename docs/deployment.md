# Deployment

## Docker

```bash
docker compose -f docker/mcp.compose.yml up -d
```

The image runs `salesforce-mcp` with `TRANSPORT=streamable-http` on port
8000 and exposes a `/health` route for orchestrator health checks.

## Environment

All configuration is via `SALESFORCE_*` environment variables — see
`.env.example`. Mount secrets (client secret, JWT private key) from your
secret store; never bake them into the image. Keep
`SALESFORCE_ALLOW_DESTRUCTIVE=False` in shared deployments.

## MCP client wiring

`mcp_config.json` at the repo root is the reference client entry; the
packaged `salesforce_agent/mcp_config.json` launches the server via
`python -m salesforce_agent.mcp_server` for the A2A agent.
