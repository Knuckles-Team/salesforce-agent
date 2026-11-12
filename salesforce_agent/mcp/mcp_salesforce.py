"""CONCEPT:SF-OS.governance.sfdc-2 MCP tools over the Salesforce API clients.

The SDK derives one typed tool per method of each resource client on the
:class:`~salesforce_agent.api_client.Api` facade (``salesforce_soql_query``,
``salesforce_records_create``, ...). This module registers the one explicit tool that
is not a single client call: the knowledge-graph CRM ingest. All API surface
(pagination, batching limits, destructive gating
CONCEPT:SF-OS.governance.destructive-operations-delete-collections, size caps) lives in
``salesforce_agent.api``.
"""

from typing import Any

from fastmcp import FastMCP
from pydantic import Field

from salesforce_agent.auth import get_client


def register_ingest_tools(mcp: FastMCP) -> None:
    """Register the native knowledge-graph CRM ingestion tool (Wire-First)."""

    @mcp.tool(tags={"misc", "kg"})
    async def salesforce_ingest_crm(
        sobjects: list[str] | None = Field(
            default=None,
            description=(
                "sObjects to ingest, from Account, Contact, Opportunity and Lead. "
                "Defaults to all four core CRM objects when omitted."
            ),
        ),
        max_records: int | None = Field(
            default=None, description="Cap on records read per sObject."
        ),
    ) -> Any:
        """Natively ingest Salesforce CRM records into medulla as typed nodes.

        Runs the per-sObject SOQL SELECT for each requested object and pushes the
        records (with their :worksAtAccount / :opportunityForAccount /
        :convertedToAccount / :ownedBy links) into the knowledge graph as typed
        :Account / :Contact / :Opportunity / :Lead (+ :Person owner) nodes via the
        fast engine client. Best-effort: ``ingested`` is ``null`` when no engine is
        reachable. CONCEPT:AU-KG.ingest.enterprise-source-extractor.
        """
        from salesforce_agent.kg_ingest import INGEST_QUERIES, ingest_records

        api = get_client()
        sobjects = sobjects or list(INGEST_QUERIES)
        summary: dict[str, Any] = {}
        for sobject in sobjects:
            soql = INGEST_QUERIES.get(sobject)
            if soql is None:
                summary[sobject] = {"error": "no ingest query for sObject"}
                continue
            result = api.soql.query(soql, max_records=max_records)
            records = result.get("records", [])
            ingested = await ingest_records(sobject, records)
            summary[sobject] = {"listed": len(records), "ingested": ingested}
        return summary


def register_salesforce_tools(mcp: FastMCP) -> None:
    """Register the Salesforce tools that are not derived from the API clients."""
    register_ingest_tools(mcp)
