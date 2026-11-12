---
name: salesforce-soql-query
skill_type: skill
description: >-
  Query Salesforce data with SOQL/SOSL over the salesforce-agent MCP server — run
  bounded SOQL queries (auto-paginated via nextRecordsUrl), queryAll over
  soft-deleted/archived rows, read a query plan with explain, and run SOSL full-text
  search across objects. Use when the agent must read/aggregate CRM records (accounts,
  contacts, opportunities, leads), profile a query's cost, or full-text search. Do NOT
  use to create/update/delete records (use salesforce-record-management) or to push
  records into the knowledge graph (use salesforce-crm-knowledge-graph).
license: MIT
tags: [salesforce, soql, sosl, crm, rest-api, mcp]
metadata:
  author: Knuckles-Team
  version: '0.1.0'
---
# Salesforce SOQL / SOSL Query

Read-side access to a Salesforce org via SOQL and SOSL. The query tool auto-follows
`nextRecordsUrl` pages up to a cap and flags `truncated` when the cap stops pagination
early — so reads are bounded and safe by default.

## When to use
- Read or aggregate CRM records (Account, Contact, Opportunity, Lead, Case, …).
- Include soft-deleted/archived rows (`query_all`).
- Inspect a query's cost/selectivity before running it at scale (`salesforce_soql_explain`).
- Full-text search across multiple objects (`salesforce_soql_search`, SOSL `FIND {...}`).

## When NOT to use
- Creating/updating/deleting records or batching writes → `salesforce-record-management`.
- Loading CRM objects into the knowledge graph as typed nodes →
  `salesforce-crm-knowledge-graph`.
- Discovering which fields/objects exist → use `salesforce_describe_sobject` first.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`salesforce-agent`** MCP server.

| Variable | Required | Notes |
|----------|----------|-------|
| `SALESFORCE_INSTANCE_URL` | ✅ | Org login/instance URL |
| `SALESFORCE_CLIENT_ID` / `SALESFORCE_CLIENT_SECRET` | ✅ | Connected-app OAuth2 |
| `SALESFORCE_USERNAME` / `SALESFORCE_PASSWORD` | optional | password/JWT flow |
| `SALESFORCE_MAX_QUERY_RECORDS` | optional | default pagination cap |

Full env matrix: the mcp-client reference for `salesforce-agent`.

## Tools
| Tool | Purpose |
|------|---------|
| `salesforce_soql_query` | Run a bounded SOQL query, auto-paginated; `query_all=true` also returns deleted and archived rows |
| `salesforce_soql_explain` | Read the query plan for a SOQL statement |
| `salesforce_soql_search` | Run a SOSL full-text search across objects |

### Key parameters
- `soql` — the SOQL text (for `salesforce_soql_query` and `salesforce_soql_explain`).
- `query_all` — `true` to include soft-deleted and archived rows.
- `max_records` — cap gathered records (defaults to `SALESFORCE_MAX_QUERY_RECORDS`).
- `sosl` — the SOSL text for `salesforce_soql_search`.
- To confirm object and field API names first, call `salesforce_describe_sobject` (see `salesforce-record-management`).

## Recipes
Open pipeline by stage (`salesforce_soql_query`): `soql` = `SELECT Id, Name, StageName, Amount, CloseDate FROM Opportunity WHERE IsClosed = false ORDER BY Amount DESC`, `max_records` = 200.

Contacts at an account (`salesforce_soql_query`): `soql` = `SELECT Id, Name, Email, Title FROM Contact WHERE AccountId = '001XXXXXXXXXXXX' LIMIT 50`.

SOSL full-text search (`salesforce_soql_search`): `sosl` = `FIND {Acme} IN ALL FIELDS RETURNING Account(Id,Name), Contact(Id,Name,Email)`.

## Gotchas
- Always list explicit fields + a `LIMIT`/`max_records`; unbounded `SELECT` is slow and
  the result is flagged `truncated` with the unfollowed `nextRecordsUrl`.
- SOQL relationship traversal uses dotted paths (`Account.Name`) and child subqueries
  `(SELECT ... FROM Contacts)`; SOSL uses the `FIND {…} RETURNING Object(fields)` form.
- `query_all` (`queryAll`) also returns deleted/archived rows — use it deliberately.

## Related
- `salesforce-record-management` — the write side (CRUD/composite/collections/bulk).
- `salesforce-crm-knowledge-graph` — push CRM records into the KG as typed nodes.
