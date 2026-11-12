# Salesforce Record Management

Create, update, upsert, and batch Salesforce sObject records over the salesforce-agent MCP server — single-record CRUD, composite (up to 25 dependent subrequests), sObject collections (up to 200 records), and Bulk API 2.0 ingest jobs for large loads. Use when the agent must write CRM data: insert an account/contact, update an opportunity stage, upsert on an external id, or load thousands of rows. Do NOT use to read/query (use salesforce-soql-query) or to ingest into the knowledge graph (use salesforce-crm-knowledge-graph). Destructive deletes are gated.

# Salesforce Record Management

The write side of a Salesforce org: single-record CRUD, heterogeneous `composite`
batches (25 dependent subrequests), homogeneous `collections` (200 records/call), and
Bulk API 2.0 for large asynchronous loads. Destructive operations (`delete`,
`collections_delete`, DELETE subrequests, bulk `delete`/`hardDelete`) are refused
unless the caller confirms (`confirm=true`).

## When to use
- Insert / update / upsert one record (upsert addresses by an external-id field).
- Batch dependent writes in one round-trip (`composite`, up to 25 subrequests).
- Batch homogeneous writes (`collections_create`/`collections_update`, up to 200).
- Load large datasets asynchronously (Bulk API 2.0: create job → upload CSV → close →
  poll status → fetch results).

## When NOT to use
- Reading/aggregating data → `salesforce-soql-query`.
- Loading records into the knowledge graph → `salesforce-crm-knowledge-graph`.
- Confirming field/object API names before a write → `salesforce_describe_sobject`.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`salesforce-agent`** MCP server (same
OAuth2 connected-app env as `salesforce-soql-query`). Deletes ask the caller
to confirm (`confirm=true`).

## Tools
| Tool | Purpose |
|------|---------|
| `salesforce_records_get` | Read one record by id |
| `salesforce_records_create` | Create a record |
| `salesforce_records_update` | Update a record by id |
| `salesforce_records_upsert` | Upsert on an external id field |
| `salesforce_records_delete` | Delete a record (gated) |
| `salesforce_records_composite` | Run up to 25 dependent subrequests in one round trip |
| `salesforce_records_collections_create` | Create up to 200 records |
| `salesforce_records_collections_update` | Update up to 200 records |
| `salesforce_records_collections_delete` | Delete up to 200 records by id (gated) |
| `salesforce_describe_global_describe` | List every sObject |
| `salesforce_describe_sobject` | Describe one sObject's fields |
| `salesforce_describe_record_counts` | Count records per sObject |
| `salesforce_describe_limits` | Read org limits and API usage |
| `salesforce_bulk_create_ingest_job` | Open a Bulk API 2.0 job |
| `salesforce_bulk_upload` | Upload CSV data to an open job |
| `salesforce_bulk_close` | Close the job so processing starts |
| `salesforce_bulk_abort` | Abort a job |
| `salesforce_bulk_status` | Poll a job |
| `salesforce_bulk_list_jobs` | List jobs |
| `salesforce_bulk_delete_job` | Delete a finished job |
| `salesforce_bulk_results` | Fetch successful, failed or unprocessed rows |

### Key parameters
- `sobject` — API name (e.g. `Account`, `Opportunity`); `record_id`, `fields` for reads.
- `data` — field-to-value object for create, update and upsert.
- `external_id_field` / `external_id` — for upsert.
- `records` / `ids` / `all_or_none` — for collections.
- `subrequests` — composite list of `{method,url,referenceId,body?}`.
- Bulk: `sobject`, `operation` (`insert`/`update`/`upsert`/`delete`), `job_id`, `csv_data`, `kind`, `locator`, `max_bytes`.

## Recipes
Create an account (`salesforce_records_create`): `sobject` = `Account`, `data` = `{"Name":"Acme Corp","Industry":"Technology"}`.

Upsert a contact by external id (`salesforce_records_upsert`): `sobject` = `Contact`, `external_id_field` = `External_Id__c`, `external_id` = `C-1001`, `data` = `{"LastName":"Doe","Email":"doe@acme.io"}`.

Batch-update opportunities (`salesforce_records_collections_update`): `records` = `[{"attributes":{"type":"Opportunity"},"Id":"006...","StageName":"Closed Won"}]`, `all_or_none` = false.

Bulk load: `salesforce_bulk_create_ingest_job` (`sobject` = `Lead`, `operation` = `insert`), then `salesforce_bulk_upload` (`job_id`, `csv_data`), then `salesforce_bulk_close`, then poll `salesforce_bulk_status` until `JobComplete`, then `salesforce_bulk_results`.

## Gotchas
- `composite` caps at 25 subrequests; `collections_*` cap at 200 records — the client
  raises a bad-request rather than silently truncating.
- Each collections record needs `attributes.type`; updates also need `Id`.
- `update` returns HTTP 204 (no body); treat a non-error as success.
- Deletes are **gated**: without `confirm=true` the SDK refuses the call and nothing is sent —
  this includes `composite` and delete ingest jobs, which are declared destructive.
- Bulk is asynchronous: after `close` poll `status` until `JobComplete`, then fetch
  `results` (`successful`/`failed`/`unprocessed`, size-capped).

## Related
- `salesforce-soql-query` — read back what you wrote.
- `salesforce-crm-knowledge-graph` — mirror records into the KG.
