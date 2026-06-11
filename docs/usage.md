# Usage

## Python API

```python
from salesforce_agent import Api, SalesforceConfig

api = Api(SalesforceConfig.from_env())          # or Api() — same thing

# SOQL with auto-pagination (capped per call)
accounts = api.soql.query("SELECT Id, Name FROM Account", max_records=500)
deleted = api.soql.query("SELECT Id FROM Account", query_all=True)
plan = api.soql.explain("SELECT Id FROM Account WHERE Name = 'Acme'")
hits = api.soql.search("FIND {Acme} IN ALL FIELDS RETURNING Account(Id, Name)")

# Record CRUD
record = api.records.get("Account", "001...", fields=["Name", "Industry"])
created = api.records.create("Account", {"Name": "Acme"})
api.records.update("Account", created["id"], {"Industry": "Energy"})
api.records.upsert("Account", "External_Id__c", "X-1", {"Name": "Acme"})

# Batching
api.records.composite([...], all_or_none=True)          # up to 25 subrequests
api.records.collections_create([...], all_or_none=True) # up to 200 records

# Metadata
api.describe.global_describe()
api.describe.sobject("Account")          # fields, relationships, picklists
api.describe.record_counts(["Account"])
api.describe.limits()                    # API usage

# Bulk API 2.0
job = api.bulk.create_ingest_job("Account", "insert")
api.bulk.upload(job["id"], "Name\nAcme\n")
api.bulk.close(job["id"])
api.bulk.status(job["id"])
api.bulk.results(job["id"], kind="successful")   # size-capped CSV

# Admin
api.admin.user_info()
api.admin.org_info()
api.admin.list_reports()
api.admin.run_report("00O...")          # sync; Salesforce caps at 2000 rows
```

Destructive calls (`records.delete`, `records.collections_delete`, bulk
`delete`/`hardDelete` jobs, DELETE composite subrequests) raise
`DestructiveOperationBlockedError` unless `allow_destructive` is enabled.

## MCP server

```bash
salesforce-mcp                                          # stdio
salesforce-mcp --transport streamable-http --port 8000  # HTTP + /health
```

Example tool calls (action-routed):

```json
{"tool": "salesforce_soql",    "action": "query",      "params_json": "{\"soql\": \"SELECT Id FROM Account\"}"}
{"tool": "salesforce_records", "action": "upsert",     "params_json": "{\"sobject\": \"Account\", \"external_id_field\": \"External_Id__c\", \"external_id\": \"X-1\", \"data\": {\"Name\": \"Acme\"}}"}
{"tool": "salesforce_bulk",    "action": "create_job", "params_json": "{\"sobject\": \"Contact\", \"operation\": \"insert\"}"}
```

## A2A agent

```bash
salesforce-agent --mcp-config mcp_config.json --port 8001
```

## Error handling

All failures map to typed exceptions in `salesforce_agent.models`:
`SalesforceAuthError` (401/OAuth), `SalesforceBadRequestError` (400),
`SalesforceRateLimitError` (403 `REQUEST_LIMIT_EXCEEDED`),
`SalesforceNotFoundError` (404), `SalesforceConflictError` (409/412/428),
`SalesforceServerError` (5xx). Tokens and secrets are redacted from every
raised message.
