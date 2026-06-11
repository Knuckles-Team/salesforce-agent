"""CONCEPT:SFDC-1.2 Typed input models for the Salesforce tool surface.

Pydantic models mirroring the ``params_json`` contracts of the action-routed
MCP tools in :mod:`salesforce_agent.mcp.mcp_salesforce`. Programmatic callers
can build and validate tool parameters with these models, then pass
``model.model_dump_json(exclude_none=True)`` as ``params_json``.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class SoqlQueryInput(BaseModel):
    """``salesforce_soql`` query/query_all/explain parameters."""

    soql: str = Field(description="SOQL statement, e.g. SELECT Id, Name FROM Account.")
    max_records: int | None = Field(
        default=None, description="Per-call cap on auto-paginated results."
    )


class SoslSearchInput(BaseModel):
    """``salesforce_soql`` search (SOSL) parameters."""

    sosl: str = Field(
        description="SOSL statement, e.g. FIND {Acme} IN ALL FIELDS RETURNING Account(Id,Name)."
    )


class RecordGetInput(BaseModel):
    """``salesforce_records`` get parameters."""

    sobject: str = Field(description="sObject API name, e.g. Account.")
    id: str = Field(description="Record Id.")
    fields: list[str] | None = Field(
        default=None, description="Optional field selection."
    )


class RecordCreateInput(BaseModel):
    """``salesforce_records`` create parameters."""

    sobject: str = Field(description="sObject API name.")
    data: dict[str, Any] = Field(description="Field name -> value payload.")


class RecordUpdateInput(BaseModel):
    """``salesforce_records`` update parameters."""

    sobject: str = Field(description="sObject API name.")
    id: str = Field(description="Record Id.")
    data: dict[str, Any] = Field(description="Field name -> value payload.")


class RecordUpsertInput(BaseModel):
    """``salesforce_records`` upsert parameters."""

    sobject: str = Field(description="sObject API name.")
    external_id_field: str = Field(description="External id field API name.")
    external_id: str = Field(description="External id value.")
    data: dict[str, Any] = Field(description="Field name -> value payload.")


class RecordDeleteInput(BaseModel):
    """``salesforce_records`` delete parameters (destructive, gated)."""

    sobject: str = Field(description="sObject API name.")
    id: str = Field(description="Record Id.")


class CompositeInput(BaseModel):
    """``salesforce_records`` composite parameters (up to 25 subrequests)."""

    subrequests: list[dict[str, Any]] = Field(
        description="Composite subrequests: method/url/referenceId entries."
    )
    all_or_none: bool = Field(
        default=False, description="Roll back everything on any subrequest error."
    )


class CollectionsInput(BaseModel):
    """``salesforce_records`` collections_create / collections_update parameters."""

    records: list[dict[str, Any]] = Field(
        description="Up to 200 records, each with an attributes.type entry."
    )
    all_or_none: bool = Field(
        default=False, description="Roll back everything on any record error."
    )


class CollectionsDeleteInput(BaseModel):
    """``salesforce_records`` collections_delete parameters (destructive, gated)."""

    ids: list[str] = Field(description="Up to 200 record Ids to delete.")
    all_or_none: bool = Field(
        default=False, description="Roll back everything on any record error."
    )


class DescribeSObjectInput(BaseModel):
    """``salesforce_describe`` sobject parameters."""

    sobject: str = Field(description="sObject API name to describe.")


class RecordCountsInput(BaseModel):
    """``salesforce_describe`` record_counts parameters."""

    sobjects: list[str] | None = Field(
        default=None, description="Optional list of sObject API names."
    )


class BulkJobCreateInput(BaseModel):
    """``salesforce_bulk`` create_job parameters."""

    sobject: str = Field(description="Target sObject API name.")
    operation: Literal["insert", "update", "upsert", "delete", "hardDelete"] = Field(
        description="Ingest operation; delete/hardDelete are destructive and gated."
    )
    external_id_field: str | None = Field(
        default=None, description="Required for upsert operations."
    )
    line_ending: Literal["LF", "CRLF"] = Field(default="LF")
    column_delimiter: str = Field(default="COMMA")


class BulkUploadInput(BaseModel):
    """``salesforce_bulk`` upload parameters."""

    job_id: str = Field(description="Ingest job Id.")
    csv: str = Field(description="CSV payload including the header row.")


class BulkJobRefInput(BaseModel):
    """``salesforce_bulk`` close/abort/status/delete_job parameters."""

    job_id: str = Field(description="Ingest job Id.")


class BulkResultsInput(BaseModel):
    """``salesforce_bulk`` results parameters."""

    job_id: str = Field(description="Ingest job Id.")
    kind: Literal["successful", "failed", "unprocessed"] = Field(default="successful")
    locator: str | None = Field(default=None, description="Resume locator.")
    max_bytes: int | None = Field(
        default=None, description="Per-call cap on downloaded result bytes."
    )


class ReportRunInput(BaseModel):
    """``salesforce_admin`` run_report parameters."""

    report_id: str = Field(description="Analytics report Id.")
    include_details: bool = Field(
        default=True, description="Include detail rows (platform-capped at 2000)."
    )
