# salesforce-agent

![PyPI - Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

**The Salesforce connector for the agent-utilities fleet** — an owned thin
httpx wrapper over the Salesforce REST API exposed as a FastMCP server and an
A2A agent. REST + SOQL/SOSL + Bulk API 2.0 + metadata describe, with safety
gates designed for autonomous agents.

No `simple-salesforce`: every endpoint is a documented thin call with its
Salesforce API doc URL cited in the docstring.

## Tools (action-routed)

| Tool | Actions |
|------|---------|
| `salesforce_soql` | `query` (auto-pagination via `nextRecordsUrl`, capped), `query_all` (deleted/archived), `explain`, `search` (SOSL) |
| `salesforce_records` | `get` (field selection), `create`, `update`, `upsert` (external id), `delete`*, `composite` (≤25 subrequests), `collections_create`/`collections_update` (≤200 records), `collections_delete`* |
| `salesforce_describe` | `global`, `sobject` (fields/relationships/picklists), `record_counts`, `limits` (API usage) |
| `salesforce_bulk` | `create_job` (insert/update/upsert/`delete`*/`hardDelete`*), `upload` (CSV), `close`, `abort`, `status`, `list_jobs`, `delete_job`, `results` (successful/failed/unprocessed, size-capped) |
| `salesforce_admin` | `user_info`, `org_info`, `list_reports`, `run_report` (sync, capped). Listing/running Flows is **out of scope for v1**. |

`*` Destructive — blocked unless `SALESFORCE_ALLOW_DESTRUCTIVE=true`.

## Auth flows

| Flow | Credentials | Notes |
|------|-------------|-------|
| OAuth2 client-credentials | consumer key + secret + My Domain URL | default server-to-server flow |
| OAuth2 refresh-token | refresh token + consumer key | instance URL from token response |
| OAuth2 JWT bearer | consumer key + username + RSA key | `pip install salesforce-agent[jwt]` |
| Static access token | token + instance URL | testing / externally managed sessions |

Sandbox orgs: `SALESFORCE_SANDBOX=true` (`test.salesforce.com`). Tokens are
cached with expiry tracking and refreshed transparently (plus one retry on
401); secrets are redacted from all errors and logs.

## Quick start

```bash
pip install salesforce-agent[all]
cp .env.example .env   # fill in one auth flow
salesforce-mcp         # stdio MCP server
```

```python
from salesforce_agent import Api

api = Api()  # configured from SALESFORCE_* env vars
rows = api.soql.query("SELECT Id, Name FROM Account", max_records=200)
api.records.upsert("Account", "External_Id__c", "X-1", {"Name": "Acme"})
```

See [docs/](docs/index.md) for the full overview, installation, usage, and
deployment guides; concept registry in [docs/concepts.md](docs/concepts.md)
(`CONCEPT:SFDC-1.x`).

## Development

```bash
pip install -e .[all,test]
pytest                       # mocked httpx suite — no live org required
pre-commit run --all-files   # must be fully green before committing
```

## License

MIT — see [LICENSE](LICENSE).
