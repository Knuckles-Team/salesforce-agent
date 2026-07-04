---
name: salesforce-record-management
description: >-
  Create, update, upsert, and batch Salesforce sObject records over the
  salesforce-agent MCP server — single-record CRUD, composite (up to 25 dependent
  subrequests), sObject collections (up to 200 records), and Bulk API 2.0 ingest jobs
  for large loads. Use when the agent must write CRM data: insert an account/contact,
  update an opportunity stage, upsert on an external id, or load thousands of rows. Do
  NOT use to read/query (use salesforce-soql-query) or to ingest into the knowledge
  graph (use salesforce-crm-knowledge-graph). Destructive deletes are gated.
license: MIT
tags: [salesforce, crm, records, bulk, mcp]
metadata:
  author: Genius
  version: '0.1.0'
---
# Salesforce Record Management

The write side of a Salesforce org: single-record CRUD, heterogeneous `composite`
batches (25 dependent subrequests), homogeneous `collections` (200 records/call), and
Bulk API 2.0 for large asynchronous loads. Destructive operations (`delete`,
`collections_delete`, DELETE subrequests, bulk `delete`/`hardDelete`) are refused
unless `SALESFORCE_ALLOW_DESTRUCTIVE` is enabled.

## When to use
- Insert / update / upsert one record (upsert addresses by an external-id field).
- Batch dependent writes in one round-trip (`composite`, up to 25 subrequests).
- Batch homogeneous writes (`collections_create`/`collections_update`, up to 200).
- Load large datasets asynchronously (Bulk API 2.0: create job → upload CSV → close →
  poll status → fetch results).

## When NOT to use
- Reading/aggregating data → `salesforce-soql-query`.
- Loading records into the knowledge graph → `salesforce-crm-knowledge-graph`.
- Confirming field/object API names before a write → `salesforce_describe` tool.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`salesforce-agent`** MCP server (same
OAuth2 connected-app env as `salesforce-soql-query`). To allow deletes set
`SALESFORCE_ALLOW_DESTRUCTIVE=true`; leave it unset for read/write-only safety.

## Tools & actions
| Condensed tool | Actions |
|----------------|---------|
| `salesforce_records` | `get`, `create`, `update`, `upsert`, `delete` (gated), `composite`, `collections_create`, `collections_update`, `collections_delete` (gated) |
| `salesforce_bulk` | `create_job`, `upload`, `close`, `abort`, `status`, `list_jobs`, `delete_job`, `results` |

### Key parameters (`params_json` — a JSON **string**)
- `sobject` — API name (e.g. `Account`, `Opportunity`).
- `data` — field→value object for create/update/upsert.
- `external_id_field` / `external_id` — for `upsert`.
- `records` / `ids` — for collections.
- `subrequests` — composite list of `{method,url,referenceId,body?}`.
- Bulk: `operation` (`insert`/`update`/`upsert`/`delete`), `job_id`, `csv`, `kind`.

## Recipes (`params_json`)
Create an account:
```json
{"sobject":"Account","data":{"Name":"Acme Corp","Industry":"Technology"}}
```
Upsert a contact by external id:
```json
{"sobject":"Contact","external_id_field":"External_Id__c","external_id":"C-1001","data":{"LastName":"Doe","Email":"doe@acme.io"}}
```
Batch-update 200 opportunities (collections):
```json
{"records":[{"attributes":{"type":"Opportunity"},"Id":"006...","StageName":"Closed Won"}],"all_or_none":false}
```
Bulk job (create then upload CSV):
```json
{"sobject":"Lead","operation":"insert"}
```
```json
{"job_id":"7501...","csv":"LastName,Company\nDoe,Acme"}
```

## Gotchas
- `params_json` is a **string** of JSON — serialize it.
- `composite` caps at 25 subrequests; `collections_*` cap at 200 records — the client
  raises a bad-request rather than silently truncating.
- Each collections record needs `attributes.type`; updates also need `Id`.
- `update` returns HTTP 204 (no body); treat a non-error as success.
- Deletes are **gated**: without `SALESFORCE_ALLOW_DESTRUCTIVE` they raise a blocked-op
  error — this includes DELETE subrequests inside `composite`.
- Bulk is asynchronous: after `close` poll `status` until `JobComplete`, then fetch
  `results` (`successful`/`failed`/`unprocessed`, size-capped).

## Related
- `salesforce-soql-query` — read back what you wrote.
- `salesforce-crm-knowledge-graph` — mirror records into the KG.
