# Salesforce Soql Query

Query Salesforce data with SOQL/SOSL over the salesforce-agent MCP server — run bounded SOQL queries (auto-paginated via nextRecordsUrl), queryAll over soft-deleted/archived rows, read a query plan with explain, and run SOSL full-text search across objects. Use when the agent must read/aggregate CRM records (accounts, contacts, opportunities, leads), profile a query's cost, or full-text search. Do NOT use to create/update/delete records (use salesforce-record-management) or to push records into the knowledge graph (use salesforce-crm-knowledge-graph).

# Salesforce SOQL / SOSL Query

Read-side access to a Salesforce org via SOQL and SOSL. The query tool auto-follows
`nextRecordsUrl` pages up to a cap and flags `truncated` when the cap stops pagination
early — so reads are bounded and safe by default.

## When to use
- Read or aggregate CRM records (Account, Contact, Opportunity, Lead, Case, …).
- Include soft-deleted/archived rows (`query_all` → `queryAll`).
- Inspect a query's cost/selectivity before running it at scale (`explain`).
- Full-text search across multiple objects (`search` → SOSL `FIND {...}`).

## When NOT to use
- Creating/updating/deleting records or batching writes → `salesforce-record-management`.
- Loading CRM objects into the knowledge graph as typed nodes →
  `salesforce-crm-knowledge-graph`.
- Discovering which fields/objects exist → use the `salesforce_describe` tool first.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`salesforce-agent`** MCP server.

| Variable | Required | Notes |
|----------|----------|-------|
| `SALESFORCE_INSTANCE_URL` | ✅ | Org login/instance URL |
| `SALESFORCE_CLIENT_ID` / `SALESFORCE_CLIENT_SECRET` | ✅ | Connected-app OAuth2 |
| `SALESFORCE_USERNAME` / `SALESFORCE_PASSWORD` | optional | password/JWT flow |
| `SALESFORCE_MAX_QUERY_RECORDS` | optional | default pagination cap |

Full env matrix: the mcp-client reference for `salesforce-agent`. `MCP_TOOL_MODE`
(`condensed`|`verbose`|`both`) selects the condensed surface used below.

## Tools & actions
| Condensed tool | Actions |
|----------------|---------|
| `salesforce_soql` | `query`, `query_all`, `explain`, `search` |

### Key parameters (`params_json` — a JSON **string**)
- `soql` — the SOQL text (for `query`/`query_all`/`explain`).
- `max_records` — cap gathered records (defaults to `SALESFORCE_MAX_QUERY_RECORDS`).
- `sosl` — the SOSL text for `search`.

## Recipes (`params_json`)
Open pipeline by stage:
```json
{"soql":"SELECT Id, Name, StageName, Amount, CloseDate FROM Opportunity WHERE IsClosed = false ORDER BY Amount DESC","max_records":200}
```
Contacts at an account:
```json
{"soql":"SELECT Id, Name, Email, Title FROM Contact WHERE AccountId = '001XXXXXXXXXXXX' LIMIT 50"}
```
SOSL full-text search:
```json
{"sosl":"FIND {Acme} IN ALL FIELDS RETURNING Account(Id,Name), Contact(Id,Name,Email)"}
```

## Gotchas
- `params_json` is a **string** of JSON, not an object — serialize it.
- Always list explicit fields + a `LIMIT`/`max_records`; unbounded `SELECT` is slow and
  the result is flagged `truncated` with the unfollowed `nextRecordsUrl`.
- SOQL relationship traversal uses dotted paths (`Account.Name`) and child subqueries
  `(SELECT ... FROM Contacts)`; SOSL uses the `FIND {…} RETURNING Object(fields)` form.
- `query_all` (`queryAll`) also returns deleted/archived rows — use it deliberately.

## Related
- `salesforce-record-management` — the write side (CRUD/composite/collections/bulk).
- `salesforce-crm-knowledge-graph` — push CRM records into the KG as typed nodes.
