# salesforce-agent

The Salesforce connector for the agent-utilities ecosystem: an owned thin
httpx wrapper over the Salesforce REST API (SOQL/SOSL, record CRUD with
composite and collections batching, metadata describe, Bulk API 2.0 ingest,
and org administration), exposed as a FastMCP server and an A2A agent.

- **No `simple-salesforce` dependency** — the fleet prefers owned thin
  clients; every endpoint cites its Salesforce documentation URL in the
  docstring.
- **Three OAuth2 flows** — client-credentials, refresh-token, and JWT bearer
  (optional `cryptography` extra), plus a static access-token mode for tests.
- **Safe by default** — deletes (single, collections, and bulk) are refused
  unless `SALESFORCE_ALLOW_DESTRUCTIVE=true`; query results and bulk result
  downloads are size-capped; tokens are redacted from errors and logs.

Start with [Overview](overview.md), then [Installation](installation.md) and
[Usage](usage.md).
