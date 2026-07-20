"""Native epistemic-graph ingestion for Salesforce CRM records.

All writes use the required ``agent_utilities.knowledge_graph.memory.native_ingest``
primitive. Nodes use canonical ``node_type`` and edges use canonical ``relationship``;
nodes and edges commit in one native transaction. Missing engine dependencies, rejected
records, conflicts, and transaction failures propagate as ``NativeIngestError``.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_utilities.knowledge_graph.memory.native_ingest import (
    NativeIngestError,
)
from agent_utilities.knowledge_graph.memory.native_ingest import (
    ingest_entities as _native_ingest_entities,
)

logger = logging.getLogger("salesforce_agent.kg")

_SOURCE = "salesforce-agent"
_DOMAIN = "salesforce"

def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    source: str = _SOURCE,
    domain: str = _DOMAIN,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Write canonical typed nodes and relationships in one native transaction."""
    return _native_ingest_entities(
        entities, relationships, source=source, domain=domain, client=client, graph=graph
    )


# --------------------------------------------------------------------------- #
# Record → typed-node mappers
# --------------------------------------------------------------------------- #
def _node_id(sobject: str, record_id: Any) -> str:
    return f"salesforce:{sobject}:{record_id}"


def _owner_edge(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    node_id: str,
    owner_id: Any,
) -> None:
    """Reuse the shared :Person for the OwnerId and link :ownedBy."""
    if not owner_id:
        return
    pid = f"salesforce:User:{owner_id}"
    entities.append({"id": pid, "node_type": "Person", "externalToolId": str(owner_id)})
    relationships.append({"source": node_id, "target": pid, "relationship": "ownedBy"})


def map_accounts(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    for rec in records or []:
        rid = rec.get("Id")
        if not rid:
            continue
        nid = _node_id("Account", rid)
        entities.append(
            {
                "id": nid,
                "node_type": "Account",
                "name": rec.get("Name"),
                "industry": rec.get("Industry"),
                "accountType": rec.get("Type"),
                "website": rec.get("Website"),
                "annualRevenue": rec.get("AnnualRevenue"),
                "salesforceId": str(rid),
                "externalToolId": str(rid),
            }
        )
        _owner_edge(entities, relationships, nid, rec.get("OwnerId"))
    return entities, relationships


def map_contacts(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    for rec in records or []:
        rid = rec.get("Id")
        if not rid:
            continue
        nid = _node_id("Contact", rid)
        entities.append(
            {
                "id": nid,
                "node_type": "Contact",
                "name": rec.get("Name"),
                "email": rec.get("Email"),
                "title": rec.get("Title"),
                "phone": rec.get("Phone"),
                "salesforceId": str(rid),
                "externalToolId": str(rid),
            }
        )
        account_id = rec.get("AccountId")
        if account_id:
            relationships.append(
                {
                    "source": nid,
                    "target": _node_id("Account", account_id),
                    "relationship": "worksAtAccount",
                }
            )
        _owner_edge(entities, relationships, nid, rec.get("OwnerId"))
    return entities, relationships


def map_opportunities(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    for rec in records or []:
        rid = rec.get("Id")
        if not rid:
            continue
        nid = _node_id("Opportunity", rid)
        entities.append(
            {
                "id": nid,
                "node_type": "Opportunity",
                "name": rec.get("Name"),
                "stageName": rec.get("StageName"),
                "amount": rec.get("Amount"),
                "closeDate": rec.get("CloseDate"),
                "isClosed": rec.get("IsClosed"),
                "isWon": rec.get("IsWon"),
                "salesforceId": str(rid),
                "externalToolId": str(rid),
            }
        )
        account_id = rec.get("AccountId")
        if account_id:
            relationships.append(
                {
                    "source": nid,
                    "target": _node_id("Account", account_id),
                    "relationship": "opportunityForAccount",
                }
            )
        _owner_edge(entities, relationships, nid, rec.get("OwnerId"))
    return entities, relationships


def map_leads(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    for rec in records or []:
        rid = rec.get("Id")
        if not rid:
            continue
        nid = _node_id("Lead", rid)
        entities.append(
            {
                "id": nid,
                "node_type": "Lead",
                "name": rec.get("Name"),
                "company": rec.get("Company"),
                "leadStatus": rec.get("Status"),
                "email": rec.get("Email"),
                "isConverted": rec.get("IsConverted"),
                "salesforceId": str(rid),
                "externalToolId": str(rid),
            }
        )
        conv_acct = rec.get("ConvertedAccountId")
        if conv_acct:
            relationships.append(
                {
                    "source": nid,
                    "target": _node_id("Account", conv_acct),
                    "relationship": "convertedToAccount",
                }
            )
        conv_opp = rec.get("ConvertedOpportunityId")
        if conv_opp:
            relationships.append(
                {
                    "source": nid,
                    "target": _node_id("Opportunity", conv_opp),
                    "relationship": "convertedToOpportunity",
                }
            )
        _owner_edge(entities, relationships, nid, rec.get("OwnerId"))
    return entities, relationships


_MAPPERS = {
    "Account": map_accounts,
    "Contact": map_contacts,
    "Opportunity": map_opportunities,
    "Lead": map_leads,
}

# The SOQL SELECT field lists used by the ingest tool per sObject.
INGEST_QUERIES: dict[str, str] = {
    "Account": (
        "SELECT Id, Name, Industry, Type, Website, AnnualRevenue, OwnerId FROM Account"
    ),
    "Contact": (
        "SELECT Id, Name, Email, Title, Phone, AccountId, OwnerId FROM Contact"
    ),
    "Opportunity": (
        "SELECT Id, Name, StageName, Amount, CloseDate, IsClosed, IsWon, "
        "AccountId, OwnerId FROM Opportunity"
    ),
    "Lead": (
        "SELECT Id, Name, Company, Status, Email, IsConverted, ConvertedAccountId, "
        "ConvertedOpportunityId, OwnerId FROM Lead"
    ),
}


def ingest_records(
    sobject: str,
    records: list[dict[str, Any]],
    *,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Map a batch of ``sobject`` records → typed nodes/links and ingest them."""
    mapper = _MAPPERS.get(sobject)
    if mapper is None:
        raise NativeIngestError(f"unsupported Salesforce object: {sobject!r}")
    entities, relationships = mapper(records)
    return ingest_entities(entities, relationships, client=client, graph=graph)
