"""Surface contracts: tool use, links, data locations and business roles."""

from scion_sdk.surface_contracts import (
    BusinessRole,
    DataLocation,
    Refusal,
    SurfaceLink,
    ToolStep,
    ToolUseContract,
)

_ACCESS_DENIED = Refusal(
    "ACCESS_DENIED", "the credential lacks access to the object or operation"
)
_NOT_FOUND = Refusal("NOT_FOUND", "the record, object or job does not exist")
_INVALID_ARGUMENT = Refusal(
    "INVALID_ARGUMENT", "the SOQL, field name or payload is rejected by Salesforce"
)
_DESTRUCTIVE_BLOCKED = Refusal(
    "DESTRUCTIVE_BLOCKED",
    "the caller did not confirm the destructive operation",
)
_NO_ENGINE = Refusal(
    "NO_ENGINE", "no knowledge-graph engine is reachable, so ingested is null"
)

CONTRACTS = (
    ToolUseContract(
        "report-pipeline",
        (
            ToolStep(
                "salesforce_describe_sobject",
                params=("name",),
                result=("name", "fields"),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
            ToolStep(
                "salesforce_soql_explain",
                params=("soql",),
                result=("plans",),
                refusals=(_ACCESS_DENIED, _INVALID_ARGUMENT),
            ),
            ToolStep(
                "salesforce_soql_query",
                params=("soql", "query_all", "max_records"),
                result=("records", "returned", "truncated"),
                refusals=(_ACCESS_DENIED, _INVALID_ARGUMENT),
            ),
        ),
        "Describe an object, then read and aggregate its records with a bounded SOQL query.",
    ),
    ToolUseContract(
        "search-crm",
        (
            ToolStep(
                "salesforce_soql_search",
                params=("sosl",),
                result=("searchRecords",),
                refusals=(_ACCESS_DENIED, _INVALID_ARGUMENT),
            ),
            ToolStep(
                "salesforce_records_get",
                params=("sobject", "record_id", "fields"),
                result=("Id",),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
        ),
        "Find records by full-text search, then read one in full.",
    ),
    ToolUseContract(
        "discover-schema",
        (
            ToolStep(
                "salesforce_describe_global_describe",
                params=(),
                result=("sobjects",),
                refusals=(_ACCESS_DENIED,),
            ),
            ToolStep(
                "salesforce_describe_sobject",
                params=("name",),
                result=("name", "fields"),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
            ToolStep(
                "salesforce_describe_record_counts",
                params=("sobjects",),
                result=("sObjects",),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
            ToolStep(
                "salesforce_describe_limits",
                params=(),
                result=("DailyApiRequests",),
                refusals=(_ACCESS_DENIED,),
            ),
        ),
        "List the org's objects, describe one, count records and read the API limits.",
    ),
    ToolUseContract(
        "maintain-records",
        (
            ToolStep(
                "salesforce_describe_sobject",
                params=("name",),
                result=("name", "fields"),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
            ToolStep(
                "salesforce_records_get",
                params=("sobject", "record_id", "fields"),
                result=("Id",),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
            ToolStep(
                "salesforce_records_create",
                params=("sobject", "data"),
                result=("id", "success"),
                refusals=(_ACCESS_DENIED, _INVALID_ARGUMENT),
            ),
            ToolStep(
                "salesforce_records_update",
                params=("sobject", "record_id", "data"),
                result=("success",),
                refusals=(_ACCESS_DENIED, _NOT_FOUND, _INVALID_ARGUMENT),
            ),
            ToolStep(
                "salesforce_records_upsert",
                params=("sobject", "external_id_field", "external_id", "data"),
                result=("id", "created"),
                refusals=(_ACCESS_DENIED, _INVALID_ARGUMENT),
            ),
        ),
        "Verify field names, then create, update or upsert one record.",
    ),
    ToolUseContract(
        "batch-write-records",
        (
            ToolStep(
                "salesforce_records_composite",
                params=("subrequests", "all_or_none"),
                result=("compositeResponse",),
                refusals=(_ACCESS_DENIED, _INVALID_ARGUMENT),
            ),
            ToolStep(
                "salesforce_records_collections_create",
                params=("records", "all_or_none"),
                result=("success", "id"),
                refusals=(_ACCESS_DENIED, _INVALID_ARGUMENT),
            ),
            ToolStep(
                "salesforce_records_collections_update",
                params=("records", "all_or_none"),
                result=("success", "id"),
                refusals=(_ACCESS_DENIED, _INVALID_ARGUMENT),
            ),
        ),
        "Write many records in one round trip: dependent subrequests or homogeneous collections.",
    ),
    ToolUseContract(
        "delete-records",
        (
            ToolStep(
                "salesforce_records_get",
                params=("sobject", "record_id", "fields"),
                result=("Id",),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
            ToolStep(
                "salesforce_records_delete",
                params=("sobject", "record_id"),
                result=("success",),
                refusals=(_ACCESS_DENIED, _NOT_FOUND, _DESTRUCTIVE_BLOCKED),
            ),
            ToolStep(
                "salesforce_records_collections_delete",
                params=("ids", "all_or_none"),
                result=("success",),
                refusals=(_ACCESS_DENIED, _DESTRUCTIVE_BLOCKED),
            ),
        ),
        "Delete records after reading them back; deletes need the destructive switch and approval.",
    ),
    ToolUseContract(
        "bulk-load-records",
        (
            ToolStep(
                "salesforce_bulk_create_ingest_job",
                params=(
                    "sobject",
                    "operation",
                    "external_id_field",
                    "line_ending",
                    "column_delimiter",
                ),
                result=("id", "state"),
                refusals=(_ACCESS_DENIED, _INVALID_ARGUMENT, _DESTRUCTIVE_BLOCKED),
            ),
            ToolStep(
                "salesforce_bulk_upload",
                params=("job_id", "csv_data"),
                result=("state",),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
            ToolStep(
                "salesforce_bulk_close",
                params=("job_id",),
                result=("state",),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
            ToolStep(
                "salesforce_bulk_status",
                params=("job_id",),
                result=("state", "numberRecordsProcessed", "numberRecordsFailed"),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
            ToolStep(
                "salesforce_bulk_results",
                params=("job_id", "kind", "locator", "max_bytes"),
                result=("data", "truncated"),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
        ),
        "Load a large CSV through a Bulk API 2.0 job and read the outcome.",
    ),
    ToolUseContract(
        "manage-bulk-jobs",
        (
            ToolStep(
                "salesforce_bulk_list_jobs",
                params=(),
                result=("records",),
                refusals=(_ACCESS_DENIED,),
            ),
            ToolStep(
                "salesforce_bulk_abort",
                params=("job_id",),
                result=("state",),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
            ToolStep(
                "salesforce_bulk_delete_job",
                params=("job_id",),
                result=("success",),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
        ),
        "Review, stop and clean up Bulk API 2.0 jobs.",
    ),
    ToolUseContract(
        "run-report",
        (
            ToolStep(
                "salesforce_admin_user_info",
                params=(),
                result=("user_id", "username"),
                refusals=(_ACCESS_DENIED,),
            ),
            ToolStep(
                "salesforce_admin_org_info",
                params=(),
                result=("organization_id", "name"),
                refusals=(_ACCESS_DENIED,),
            ),
            ToolStep(
                "salesforce_admin_list_reports",
                params=(),
                result=("reports",),
                refusals=(_ACCESS_DENIED,),
            ),
            ToolStep(
                "salesforce_admin_run_report",
                params=("report_id", "include_details"),
                result=("allData", "factMap"),
                refusals=(_ACCESS_DENIED, _NOT_FOUND),
            ),
        ),
        "Identify the integration user and org, then list and run an analytics report.",
    ),
    ToolUseContract(
        "capture-crm-to-graph",
        (
            ToolStep(
                "salesforce_ingest_crm",
                params=("sobjects", "max_records"),
                result=("listed", "ingested"),
                refusals=(_ACCESS_DENIED, _NO_ENGINE),
            ),
        ),
        "Push the core CRM objects into the knowledge graph as typed nodes.",
    ),
)

LINKS = (
    SurfaceLink(
        "report-pipeline",
        tools=(
            "salesforce_describe_sobject",
            "salesforce_soql_explain",
            "salesforce_soql_query",
        ),
        prompts=("salesforce-operator", "salesforce-sales-analyst"),
        skills=("salesforce-soql-query",),
    ),
    SurfaceLink(
        "search-crm",
        tools=("salesforce_soql_search", "salesforce_records_get"),
        prompts=("salesforce-operator", "salesforce-sales-analyst"),
        skills=("salesforce-soql-query",),
    ),
    SurfaceLink(
        "discover-schema",
        tools=(
            "salesforce_describe_global_describe",
            "salesforce_describe_sobject",
            "salesforce_describe_record_counts",
            "salesforce_describe_limits",
        ),
        prompts=(
            "salesforce-operator",
            "salesforce-sales-analyst",
            "salesforce-crm-data-steward",
        ),
        skills=("salesforce-soql-query", "salesforce-record-management"),
    ),
    SurfaceLink(
        "maintain-records",
        tools=(
            "salesforce_describe_sobject",
            "salesforce_records_get",
            "salesforce_records_create",
            "salesforce_records_update",
            "salesforce_records_upsert",
        ),
        prompts=("salesforce-operator", "salesforce-crm-data-steward"),
        skills=("salesforce-record-management",),
    ),
    SurfaceLink(
        "batch-write-records",
        tools=(
            "salesforce_records_composite",
            "salesforce_records_collections_create",
            "salesforce_records_collections_update",
        ),
        prompts=("salesforce-operator", "salesforce-crm-data-steward"),
        skills=("salesforce-record-management",),
    ),
    SurfaceLink(
        "delete-records",
        tools=(
            "salesforce_records_get",
            "salesforce_records_delete",
            "salesforce_records_collections_delete",
        ),
        prompts=("salesforce-operator", "salesforce-crm-data-steward"),
        skills=("salesforce-record-management",),
    ),
    SurfaceLink(
        "bulk-load-records",
        tools=(
            "salesforce_bulk_create_ingest_job",
            "salesforce_bulk_upload",
            "salesforce_bulk_close",
            "salesforce_bulk_status",
            "salesforce_bulk_results",
        ),
        prompts=("salesforce-operator", "salesforce-crm-data-steward"),
        skills=("salesforce-record-management",),
    ),
    SurfaceLink(
        "manage-bulk-jobs",
        tools=(
            "salesforce_bulk_list_jobs",
            "salesforce_bulk_abort",
            "salesforce_bulk_delete_job",
        ),
        prompts=("salesforce-operator", "salesforce-crm-data-steward"),
        skills=("salesforce-record-management",),
    ),
    SurfaceLink(
        "run-report",
        tools=(
            "salesforce_admin_user_info",
            "salesforce_admin_org_info",
            "salesforce_admin_list_reports",
            "salesforce_admin_run_report",
        ),
        prompts=("salesforce-operator", "salesforce-sales-analyst"),
        skills=("salesforce-soql-query", "salesforce-agent-operations"),
    ),
    SurfaceLink(
        "capture-crm-to-graph",
        tools=("salesforce_ingest_crm",),
        prompts=(
            "salesforce-operator",
            "salesforce-sales-analyst",
            "salesforce-crm-data-steward",
        ),
        skills=("salesforce-crm-knowledge-graph",),
    ),
    SurfaceLink(
        "salesforce-agent-operations",
        tools=(
            "salesforce_describe_sobject",
            "salesforce_soql_explain",
            "salesforce_soql_query",
            "salesforce_soql_search",
            "salesforce_records_get",
            "salesforce_describe_global_describe",
            "salesforce_describe_record_counts",
            "salesforce_describe_limits",
            "salesforce_records_create",
            "salesforce_records_update",
            "salesforce_records_upsert",
            "salesforce_records_composite",
            "salesforce_records_collections_create",
            "salesforce_records_collections_update",
            "salesforce_records_delete",
            "salesforce_records_collections_delete",
            "salesforce_bulk_create_ingest_job",
            "salesforce_bulk_upload",
            "salesforce_bulk_close",
            "salesforce_bulk_status",
            "salesforce_bulk_results",
            "salesforce_bulk_list_jobs",
            "salesforce_bulk_abort",
            "salesforce_bulk_delete_job",
            "salesforce_admin_user_info",
            "salesforce_admin_org_info",
            "salesforce_admin_list_reports",
            "salesforce_admin_run_report",
            "salesforce_ingest_crm",
        ),
        skills=("salesforce-agent-operations",),
    ),
)

LOCATIONS = (
    DataLocation(
        "salesforce-crm-records",
        ("Account", "Contact", "Opportunity", "Lead", "Case", "Campaign"),
        "SALESFORCE_INSTANCE_URL",
        "salesforce_soql_query",
        federation_key="Id",
    ),
    DataLocation(
        "salesforce-reports",
        ("Report",),
        "SALESFORCE_INSTANCE_URL",
        "salesforce_admin_list_reports",
        federation_key="Id",
    ),
)

ROLES = (
    BusinessRole(
        "sales-analyst",
        tasks=(
            "report-pipeline",
            "search-crm",
            "discover-schema",
            "run-report",
            "capture-crm-to-graph",
        ),
    ),
    BusinessRole(
        "crm-data-steward",
        tasks=(
            "discover-schema",
            "maintain-records",
            "batch-write-records",
            "delete-records",
            "bulk-load-records",
            "manage-bulk-jobs",
            "capture-crm-to-graph",
        ),
    ),
)
