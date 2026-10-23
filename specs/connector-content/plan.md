# CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT — Design and implementation plan

Governing spec: [spec.md](spec.md).

## Architecture

`pyproject.toml` declares `salesforce-mcp` as the connector identity. `create_mcp_server` resolves the packaged content of `salesforce_agent` from it.
