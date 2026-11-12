---
name: salesforce-agent-operations
skill_type: skill
description: >-
  Operate salesforce-agent through its governed MCP and Arbora capabilities, including salesforce crm knowledge graph, salesforce record management, salesforce soql query. Use when a request requires this provider's read, change, automation, ingestion, troubleshooting, or evidence workflows.
---

# Salesforce Agent Operations

Use the provider's governed MCP tools through Arbora delegation.

## Workflow

1. Establish the verified GraphSession and tenant before discovery or retrieval.
2. Discover the current tool surface; never assume a stale tool name or schema.
3. Prefer read-only inspection first. For changes, present impact and use the provider's
   dry-run or preview mode when available.
4. Execute mutations as fenced WorkItems so retries remain idempotent and auditable.
5. Ingest source data only through the signed connector preset and ChangeEnvelope path.
6. Verify the durable result and its trace/evidence before reporting completion.

## Tools

- Read: `salesforce_soql_query`, `salesforce_soql_explain`, `salesforce_soql_search`, `salesforce_records_get`, `salesforce_describe_global_describe`, `salesforce_describe_sobject`, `salesforce_describe_record_counts`, `salesforce_describe_limits`.
- Write: `salesforce_records_create`, `salesforce_records_update`, `salesforce_records_upsert`, `salesforce_records_composite`, `salesforce_records_collections_create`, `salesforce_records_collections_update`.
- Gated delete (asks the caller to confirm): `salesforce_records_delete`, `salesforce_records_collections_delete`.
- Bulk: `salesforce_bulk_create_ingest_job`, `salesforce_bulk_upload`, `salesforce_bulk_close`, `salesforce_bulk_abort`, `salesforce_bulk_status`, `salesforce_bulk_list_jobs`, `salesforce_bulk_delete_job`, `salesforce_bulk_results`.
- Org and reports: `salesforce_admin_user_info`, `salesforce_admin_org_info`, `salesforce_admin_list_reports`, `salesforce_admin_run_report`.
- Graph: `salesforce_ingest_crm`.

## Safety contract

- Never persist credentials, endpoints, raw personal identifiers, hostnames, or local paths.
- Resolve TLS trust and verification from environment/configuration; never hardcode bypasses.
- Treat unknown ACL, tenant, schema, or tool-contract state as a hard failure.
- Require explicit approval for destructive, externally visible, or irreversible actions.
- Keep runtime traces policy-scoped and privacy-sanitized.

## Specialized workflows

Read [the workflow catalog](references/catalog.md) only when the request needs a
provider-specific procedure, parameter map, script, or reference asset.
