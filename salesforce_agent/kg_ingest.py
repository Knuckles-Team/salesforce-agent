"""Epistemic-graph ingestion for Salesforce CRM records.

The salesforce-agent connector pushes CRM records into the ONE epistemic-graph
knowledge graph as typed OWL nodes (``:Account``/``:Contact``/``:Opportunity``/
``:Lead`` + ``:Person`` owner) + links through ``agent_connector_sdk.ingest`` --
the generated ``SourceIngest`` client, not a local ingestion helper. Nodes use
canonical ``node_type`` and edges use canonical ``relationship``.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_connector_sdk.ingest import (
    ChangeSet,
    Entity,
    IngestBinding,
    IngestError,
    KnowledgeIngest,
    Relationship,
    current_ingest,
)

logger = logging.getLogger("salesforce_agent.kg")

_BINDING = IngestBinding(connector="salesforce-agent", stream="salesforce")

_ENTITY_RESERVED_KEYS = frozenset({"id", "node_type"})
_RELATIONSHIP_RESERVED_KEYS = frozenset({"source", "target", "relationship"})


def _to_entity(record: dict[str, Any]) -> Entity:
    return Entity(
        id=record.get("id"),
        node_type=record.get("node_type"),
        properties={
            key: value
            for key, value in record.items()
            if key not in _ENTITY_RESERVED_KEYS
        },
    )


def _to_relationship(record: dict[str, Any]) -> Relationship:
    properties = {
        key: value
        for key, value in record.items()
        if key not in _RELATIONSHIP_RESERVED_KEYS
    }
    return Relationship(
        source=record["source"],
        target=record["target"],
        relationship=record["relationship"],
        properties=properties or None,
    )


async def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Write canonical typed nodes and relationships via the SDK ingest facade.

    Uses canonical ``node_type`` / ``relationship`` structural fields and surfaces
    a malformed change set or a refused commit as ``IngestError``.
    """
    if not entities:
        raise IngestError("ingest_entities needs at least one entity")
    change_set = ChangeSet(
        entities=tuple(_to_entity(entity) for entity in entities),
        relationships=tuple(
            _to_relationship(relationship) for relationship in relationships or ()
        ),
    )
    service = ingest or current_ingest()
    receipt = await service.submit(_BINDING, change_set)
    return {"nodes": receipt.affected_count, "edges": receipt.relationship_count}


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


async def ingest_records(
    sobject: str,
    records: list[dict[str, Any]],
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Map a batch of ``sobject`` records → typed nodes/links and ingest them."""
    mapper = _MAPPERS.get(sobject)
    if mapper is None:
        raise IngestError(f"unsupported Salesforce object: {sobject!r}")
    entities, relationships = mapper(records)
    return await ingest_entities(entities, relationships, ingest=ingest)
