# salesforce-agent

Salesforce **API + MCP Server + A2A Agent** for the agent-utilities ecosystem — a
typed, action-routed connector for the Salesforce REST, SOQL/SOSL, and Bulk API 2.0
surface.

!!! info "Official documentation"
    This site is the canonical reference for `salesforce-agent`, maintained alongside
    every release.

[![PyPI](https://img.shields.io/pypi/v/salesforce-agent)](https://pypi.org/project/salesforce-agent/)
![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')
[![License](https://img.shields.io/pypi/l/salesforce-agent)](https://github.com/Knuckles-Team/salesforce-agent/blob/main/LICENSE)
[![GitHub](https://img.shields.io/badge/source-GitHub-181717?logo=github)](https://github.com/Knuckles-Team/salesforce-agent)

## Overview

`salesforce-agent` wraps the Salesforce REST API with typed, deterministic MCP tools
and an optional Pydantic-AI agent server. It provides:

- **`Api`** — a Python client (`salesforce_agent.api_client.Api`) composed from
  per-domain mixins covering SOQL/SOSL queries, record CRUD with composite and
  collections batching, metadata describe, Bulk API 2.0 ingest, and org
  administration. No `simple-salesforce`: every endpoint is a documented thin call
  with its Salesforce API doc URL cited in the docstring.
- **Action-routed MCP tools** — consolidated, togglable tool modules
  (`salesforce_soql`, `salesforce_records`, `salesforce_describe`,
  `salesforce_bulk`, `salesforce_admin`) that minimize token overhead in LLM
  contexts.
- **An A2A agent server** — a Pydantic-AI graph agent (console script
  `salesforce-agent`) that calls the MCP tool surface and exposes an AG-UI web
  interface.

Safety is built in: destructive paths (record delete, collections delete, bulk
delete/hardDelete) are refused unless `SALESFORCE_ALLOW_DESTRUCTIVE=true`, result
surfaces are size-capped, and secrets are redacted from errors and logs.

The connector remains inactive when credentials are absent: configure
`SALESFORCE_INSTANCE_URL` and one OAuth2 flow to connect it to an org.

## Explore the documentation

<div class="grid cards" markdown>

- :material-rocket-launch: **[Installation](installation.md)** — pip, source, extras, and the prebuilt Docker image.
- :material-server-network: **[Deployment](deployment.md)** — run the MCP and agent servers, Docker Compose.
- :material-console: **[Usage](usage.md)** — the MCP tools, the `Api` client, and the CLI.
- :material-sitemap: **[Overview](overview.md)** — the action-routed tool surface and architecture.
- :material-tag-multiple: **[Concepts](concepts.md)** — the `CONCEPT:SFDC-*` registry.

</div>

## Quick start

```bash
pip install "salesforce-agent[mcp]"
salesforce-mcp                     # stdio MCP server (default transport)
```

Connect it to a Salesforce org:

```bash
export SALESFORCE_INSTANCE_URL=https://yourorg.my.salesforce.com
export SALESFORCE_CLIENT_ID=<consumer-key>
export SALESFORCE_CLIENT_SECRET=<consumer-secret>
salesforce-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

See **[Installation](installation.md)** and **[Deployment](deployment.md)** for the
full matrix (PyPI extras, Docker image, all transports, the agent server).

!!! note "Backing platform"
    Salesforce is a managed SaaS platform — there is no self-hosted deployment
    recipe, so this site intentionally omits the *Backing Platform* page that
    connectors to self-hostable systems carry.
