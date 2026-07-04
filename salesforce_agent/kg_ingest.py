"""Native epistemic-graph ingestion for Salesforce CRM records (typed graph nodes).

CONCEPT:AU-KG.ingest.enterprise-source-extractor. The salesforce-agent connector
natively pushes its CRM data into the ONE epistemic-graph knowledge graph as **typed
OWL nodes** (``:Account``, ``:Contact``, ``:Opportunity``, ``:Lead``, ``:Case``,
``:Campaign``) plus their links (``:worksAtAccount`` / ``:opportunityForAccount`` /
``:convertedToAccount`` / ``:ownedBy`` …), matching the classes federated by
``salesforce_agent.ontology`` (``salesforce.ttl``).

It rides the shared native-ingest primitive
(``agent_utilities.knowledge_graph.memory.native_ingest``) when present; because that
primitive is not yet in the installed ``agent_utilities`` everywhere, the import is
GUARDED and a self-contained txn fallback over the lightweight engine client
(``GraphComputeEngine()._client`` + ``txn``) is used otherwise. Everything is
dependency-/engine-guarded: with no KG stack or no reachable engine every entry point
**no-ops** (returns ``None``), so the connector runs with zero KG infrastructure. Node
ids follow ``salesforce:<class>:<recordId>``.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("salesforce_agent.kg")

_SOURCE = "salesforce-agent"
_DOMAIN = "salesforce"
_DEFAULT_GRAPH = "__commons__"

# Prefer the shared fleet primitive; fall back to the self-contained path below.
try:  # pragma: no cover - exercised only where the primitive is installed
    from agent_utilities.knowledge_graph.memory.native_ingest import (
        ingest_entities as _shared_ingest_entities,
    )
except Exception:  # noqa: BLE001 - primitive not yet installed everywhere
    _shared_ingest_entities = None


def _client() -> tuple[Any | None, str]:
    """Return ``(engine_client, graph_name)`` or ``(None, "")`` when unavailable."""
    try:
        from agent_utilities.knowledge_graph.core.graph_compute import (
            GraphComputeEngine,
        )
    except Exception as e:  # noqa: BLE001 - KG stack absent
        logger.debug("KG ingest unavailable (import): %s", e)
        return None, ""
    try:
        engine = GraphComputeEngine()
        client = getattr(engine, "_client", None)
        if client is None:
            return None, ""
        return client, (getattr(engine, "graph_name", None) or _DEFAULT_GRAPH)
    except Exception as e:  # noqa: BLE001 - engine unreachable
        logger.debug("KG ingest: engine unreachable: %s", e)
        return None, ""


def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    source: str = _SOURCE,
    domain: str = _DOMAIN,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
    """Write typed nodes (+ edges) into epistemic-graph.

    ``entities``: ``[{"id":..., "type":<owl:Class>, ...props}]``.
    ``relationships``: ``[{"source":id, "target":id, "type":<link>}]``.
    Returns ``{"nodes":n, "edges":m}`` or ``None`` (no engine / failure; never raises).
    Delegates to the shared fleet primitive when installed and no client is injected;
    otherwise runs the self-contained txn fallback. ``client``/``graph`` may be
    injected (tests).
    """
    entities = [e for e in (entities or []) if e.get("id")]
    if not entities:
        return None

    if client is None and _shared_ingest_entities is not None:
        try:
            return _shared_ingest_entities(
                entities, relationships, source=source, domain=domain
            )
        except Exception as e:  # noqa: BLE001 - fall back to local path
            logger.debug("KG ingest: shared primitive failed, local fallback: %s", e)

    if client is None:
        client, graph = _client()
    if client is None:
        return None
    graph = graph or _DEFAULT_GRAPH

    try:
        txn = client.txn.begin(graph=graph)
        for ent in entities:
            props = {k: v for k, v in ent.items() if k != "id" and v is not None}
            props.setdefault("source", source)
            props.setdefault("domain", domain)
            client.txn.add_node(txn, ent["id"], props)
        committed = client.txn.commit(txn)
    except Exception as e:  # noqa: BLE001 - engine/txn failure is non-fatal
        logger.warning("KG ingest: txn failed: %s", e)
        return None
    if not committed:
        logger.warning("KG ingest: txn not committed (conflict)")
        return None

    edges = 0
    for rel in relationships or []:
        try:
            client.edges.add(
                rel["source"], rel["target"], {"type": rel.get("type", "RELATED")}
            )
            edges += 1
        except Exception as e:  # noqa: BLE001 - pure edge link, best-effort
            logger.debug("KG ingest: edge skipped: %s", e)

    logger.info("KG ingest: wrote %d nodes, %d edges", len(entities), edges)
    return {"nodes": len(entities), "edges": edges}


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
    entities.append({"id": pid, "type": "Person", "externalToolId": str(owner_id)})
    relationships.append({"source": node_id, "target": pid, "type": "ownedBy"})


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
                "type": "Account",
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
                "type": "Contact",
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
                    "type": "worksAtAccount",
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
                "type": "Opportunity",
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
                    "type": "opportunityForAccount",
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
                "type": "Lead",
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
                    "type": "convertedToAccount",
                }
            )
        conv_opp = rec.get("ConvertedOpportunityId")
        if conv_opp:
            relationships.append(
                {
                    "source": nid,
                    "target": _node_id("Opportunity", conv_opp),
                    "type": "convertedToOpportunity",
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
) -> dict[str, int] | None:
    """Map a batch of ``sobject`` records → typed nodes/links and ingest them."""
    mapper = _MAPPERS.get(sobject)
    if mapper is None:
        logger.debug("KG ingest: no mapper for sObject %r", sobject)
        return None
    entities, relationships = mapper(records)
    return ingest_entities(entities, relationships, client=client, graph=graph)
