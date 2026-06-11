"""CONCEPT:SFDC-1.2 Action-routed MCP tools over the Salesforce API clients.

Each tool is a thin shim: it parses params, picks the resource client on the
:class:`~salesforce_agent.api_client.Api` facade, calls the matching method,
and returns the result. All API surface (pagination, batching limits,
destructive gating CONCEPT:SFDC-1.3, size caps) lives in
``salesforce_agent.api`` — these tools add no business logic.
"""

import json
from typing import Any

from fastmcp import FastMCP
from pydantic import Field

from salesforce_agent.auth import get_client


def _p(params_json: str) -> dict[str, Any]:
    return json.loads(params_json) if params_json else {}


def register_soql_tools(mcp: FastMCP) -> None:
    """Register the SOQL/SOSL query tool."""

    @mcp.tool(tags={"query"})
    async def salesforce_soql(
        action: str = Field(
            description=(
                "Query action: 'query' (SOQL, auto-paginated via "
                "nextRecordsUrl), 'query_all' (includes soft-deleted/"
                "archived rows), 'explain' (query plan), 'search' (SOSL "
                "full-text search)."
            )
        ),
        params_json: str = Field(
            default="{}",
            description=(
                'JSON args. query/query_all/explain: {"soql": "SELECT ...", '
                '"max_records": 500}; search: {"sosl": "FIND {Acme} IN ALL '
                'FIELDS RETURNING Account(Id,Name)"}.'
            ),
        ),
    ) -> Any:
        """Run SOQL queries (paginated, capped) and SOSL searches."""
        api = get_client()
        p = _p(params_json)
        if action in ("query", "query_all"):
            return api.soql.query(
                p["soql"],
                query_all=(action == "query_all"),
                max_records=p.get("max_records"),
            )
        if action == "explain":
            return api.soql.explain(p["soql"])
        if action == "search":
            return api.soql.search(p["sosl"])
        raise ValueError(f"Unknown soql action: {action!r}.")


def register_records_tools(mcp: FastMCP) -> None:
    """Register the record CRUD / composite / collections tool."""

    @mcp.tool(tags={"records"})
    async def salesforce_records(
        action: str = Field(
            description=(
                "Record action: 'get', 'create', 'update', 'upsert', "
                "'delete' (gated by SALESFORCE_ALLOW_DESTRUCTIVE), "
                "'composite' (up to 25 subrequests), 'collections_create', "
                "'collections_update' (up to 200 records), "
                "'collections_delete' (gated)."
            )
        ),
        params_json: str = Field(
            default="{}",
            description=(
                'JSON args. get: {"sobject": "Account", "id": ..., '
                '"fields": ["Name"]}; create/update: {"sobject": ..., '
                '"id": ..., "data": {...}}; upsert: {"sobject": ..., '
                '"external_id_field": ..., "external_id": ..., "data": '
                '{...}}; composite: {"subrequests": [{"method": ..., '
                '"url": ..., "referenceId": ...}], "all_or_none": false}; '
                'collections_*: {"records": [...]} or {"ids": [...]}.'
            ),
        ),
    ) -> Any:
        """CRUD on sObject records, composite batches, and collections."""
        api = get_client()
        p = _p(params_json)
        sobject = p.get("sobject", "")
        if action == "get":
            return api.records.get(sobject, p["id"], fields=p.get("fields"))
        if action == "create":
            return api.records.create(sobject, p["data"])
        if action == "update":
            return api.records.update(sobject, p["id"], p["data"])
        if action == "upsert":
            return api.records.upsert(
                sobject, p["external_id_field"], p["external_id"], p["data"]
            )
        if action == "delete":
            return api.records.delete(sobject, p["id"])
        if action == "composite":
            return api.records.composite(
                p["subrequests"], all_or_none=p.get("all_or_none", False)
            )
        if action == "collections_create":
            return api.records.collections_create(
                p["records"], all_or_none=p.get("all_or_none", False)
            )
        if action == "collections_update":
            return api.records.collections_update(
                p["records"], all_or_none=p.get("all_or_none", False)
            )
        if action == "collections_delete":
            return api.records.collections_delete(
                p["ids"], all_or_none=p.get("all_or_none", False)
            )
        raise ValueError(f"Unknown records action: {action!r}.")


def register_describe_tools(mcp: FastMCP) -> None:
    """Register the metadata describe / limits tool."""

    @mcp.tool(tags={"metadata"})
    async def salesforce_describe(
        action: str = Field(
            description=(
                "Describe action: 'global' (list all sObjects), 'sobject' "
                "(fields/relationships/picklists for one object), "
                "'record_counts', 'limits' (org limits + API usage)."
            )
        ),
        params_json: str = Field(
            default="{}",
            description=(
                'JSON args. sobject: {"sobject": "Account"}; record_counts: '
                '{"sobjects": ["Account", "Contact"]} (optional).'
            ),
        ),
    ) -> Any:
        """Discover org schema, record counts, and limits/API usage."""
        api = get_client()
        p = _p(params_json)
        if action == "global":
            return api.describe.global_describe()
        if action == "sobject":
            return api.describe.sobject(p["sobject"])
        if action == "record_counts":
            return api.describe.record_counts(p.get("sobjects"))
        if action == "limits":
            return api.describe.limits()
        raise ValueError(f"Unknown describe action: {action!r}.")


def register_bulk_tools(mcp: FastMCP) -> None:
    """Register the Bulk API 2.0 ingest tool."""

    @mcp.tool(tags={"bulk"})
    async def salesforce_bulk(
        action: str = Field(
            description=(
                "Bulk API 2.0 action: 'create_job' (insert/update/upsert; "
                "delete/hardDelete gated by SALESFORCE_ALLOW_DESTRUCTIVE), "
                "'upload' (CSV), 'close' (start processing), 'abort', "
                "'status', 'list_jobs', 'delete_job', 'results' "
                "(successful/failed/unprocessed CSV, size-capped)."
            )
        ),
        params_json: str = Field(
            default="{}",
            description=(
                'JSON args. create_job: {"sobject": ..., "operation": '
                '"insert", "external_id_field": ...}; upload: {"job_id": '
                '..., "csv": "Name\\nAcme"}; close/abort/status/delete_job: '
                '{"job_id": ...}; results: {"job_id": ..., "kind": '
                '"successful"|"failed"|"unprocessed", "locator": ..., '
                '"max_bytes": ...}.'
            ),
        ),
    ) -> Any:
        """Drive Bulk API 2.0 ingest jobs: create, upload, close, results."""
        api = get_client()
        p = _p(params_json)
        if action == "create_job":
            return api.bulk.create_ingest_job(
                p["sobject"],
                p["operation"],
                external_id_field=p.get("external_id_field"),
                line_ending=p.get("line_ending", "LF"),
                column_delimiter=p.get("column_delimiter", "COMMA"),
            )
        if action == "upload":
            return api.bulk.upload(p["job_id"], p["csv"])
        if action == "close":
            return api.bulk.close(p["job_id"])
        if action == "abort":
            return api.bulk.abort(p["job_id"])
        if action == "status":
            return api.bulk.status(p["job_id"])
        if action == "list_jobs":
            return api.bulk.list_jobs()
        if action == "delete_job":
            return api.bulk.delete_job(p["job_id"])
        if action == "results":
            return api.bulk.results(
                p["job_id"],
                kind=p.get("kind", "successful"),
                locator=p.get("locator"),
                max_bytes=p.get("max_bytes"),
            )
        raise ValueError(f"Unknown bulk action: {action!r}.")


def register_admin_tools(mcp: FastMCP) -> None:
    """Register the identity / org / analytics tool."""

    @mcp.tool(tags={"admin"})
    async def salesforce_admin(
        action: str = Field(
            description=(
                "Admin action: 'user_info' (integration user identity), "
                "'org_info', 'list_reports' (recently viewed analytics "
                "reports), 'run_report' (synchronous, platform-capped at "
                "2000 detail rows). Listing/running Flows is OUT of scope "
                "for v1 of this connector."
            )
        ),
        params_json: str = Field(
            default="{}",
            description=(
                'JSON args. run_report: {"report_id": ..., ' '"include_details": true}.'
            ),
        ),
    ) -> Any:
        """Inspect the current user/org and run analytics reports."""
        api = get_client()
        p = _p(params_json)
        if action == "user_info":
            return api.admin.user_info()
        if action == "org_info":
            return api.admin.org_info()
        if action == "list_reports":
            return api.admin.list_reports()
        if action == "run_report":
            return api.admin.run_report(
                p["report_id"], include_details=p.get("include_details", True)
            )
        raise ValueError(f"Unknown admin action: {action!r}.")


def register_salesforce_tools(mcp: FastMCP) -> None:
    """Register every Salesforce tool group on one FastMCP server."""
    register_soql_tools(mcp)
    register_records_tools(mcp)
    register_describe_tools(mcp)
    register_bulk_tools(mcp)
    register_admin_tools(mcp)
