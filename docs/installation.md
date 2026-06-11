# Installation

## PyPI / pip

```bash
pip install salesforce-agent            # core client only
pip install salesforce-agent[mcp]       # + FastMCP server
pip install salesforce-agent[agent]     # + Pydantic AI A2A agent server
pip install salesforce-agent[jwt]       # + cryptography for the JWT bearer flow
pip install salesforce-agent[all]       # everything
```

## From source

```bash
git clone <repo-url> && cd salesforce-agent
pip install -e .[all,test]
```

## Configuration

Copy `.env.example` to `.env` and fill in one auth flow. The minimum viable
configurations are:

```bash
# Client-credentials (Connected App, server-to-server)
SALESFORCE_INSTANCE_URL=https://yourorg.my.salesforce.com
SALESFORCE_CLIENT_ID=<consumer key>
SALESFORCE_CLIENT_SECRET=<consumer secret>

# JWT bearer
SALESFORCE_CLIENT_ID=<consumer key>
SALESFORCE_JWT_SUBJECT=integration.user@yourorg.com
SALESFORCE_JWT_PRIVATE_KEY_PATH=/run/secrets/sf-server.key

# Refresh token
SALESFORCE_CLIENT_ID=<consumer key>
SALESFORCE_REFRESH_TOKEN=<refresh token>
```

Set `SALESFORCE_SANDBOX=true` for sandbox orgs and
`SALESFORCE_ALLOW_DESTRUCTIVE=true` only where deletes are genuinely wanted.

## Verify

```bash
pytest                          # mocked suite, no live org needed
salesforce-mcp --help           # MCP server entry point
salesforce-agent --help         # A2A agent entry point
```
