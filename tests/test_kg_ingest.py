"""Epistemic-graph typed-node ingestion -- Wire-First coverage for salesforce-agent.

Exercises the real ``ingest_entities`` / ``ingest_records`` seam against a fake
``agent_connector_sdk.ingest`` transport (no engine required). The real SDK
request builder (``agent_connector_sdk.ingest.request.build_request``) still
runs, so a malformed change set is still caught by the SDK's own contract, not
re-derived here; only the final network commit is faked.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from agent_connector_sdk.ingest import IngestError, KnowledgeIngest
from epistemic_graph.generated.source_ingestion import SourceIngestionRequest

from salesforce_agent.kg_ingest import (
    INGEST_QUERIES,
    ingest_entities,
    ingest_records,
    map_leads,
)


class _FakeTransport:
    """Records every submitted request; no epistemic-graph engine required."""

    def __init__(self) -> None:
        self.requests: list[SourceIngestionRequest] = []

    async def source_status(self, _connector: str, _stream: str) -> Any:
        return SimpleNamespace(accepted_checkpoint=None)

    async def submit(self, request: SourceIngestionRequest) -> Any:
        self.requests.append(request)
        return SimpleNamespace(
            affected_count=len(request.records),
            relationship_count=len(request.relationships),
        )

    async def store_blob(self, _data: bytes) -> str:
        raise AssertionError("salesforce-agent ingestion carries no media")


@pytest.fixture
def ingest() -> tuple[KnowledgeIngest, _FakeTransport]:
    transport = _FakeTransport()
    return KnowledgeIngest(transport, loop=None), transport


@pytest.mark.asyncio
async def test_ingest_entities_writes_nodes_and_edges(ingest):
    service, transport = ingest
    res = await ingest_entities(
        [
            {"id": "a", "node_type": "Account", "name": "Acme"},
            {"id": "b", "node_type": "Contact"},
        ],
        [{"source": "b", "target": "a", "relationship": "worksAtAccount"}],
        ingest=service,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert len(transport.requests) == 1
    request = transport.requests[0]
    record_ids = {record.record_id for record in request.records}
    assert record_ids == {"a", "b"}
    a_record = next(r for r in request.records if r.record_id == "a")
    assert a_record.payload["name"] == "Acme"
    assert request.relationships[0].relation_reference.endswith(
        "resources/Contact/relations/worksAtAccount"
    )


@pytest.mark.asyncio
async def test_ingest_records_accounts_with_owner(ingest):
    service, transport = ingest
    res = await ingest_records(
        "Account",
        [{"Id": "001A", "Name": "Acme", "Industry": "Tech", "OwnerId": "005U"}],
        ingest=service,
    )
    # 1 account + 1 owner Person node, 1 ownedBy edge
    assert res == {"nodes": 2, "edges": 1}
    request = transport.requests[0]
    acct = next(
        r for r in request.records if r.record_id == "salesforce:Account:001A"
    )
    assert acct.payload["industry"] == "Tech"
    assert acct.payload["salesforceId"] == "001A"
    assert any(
        r.record_id == "salesforce:User:005U" for r in request.records
    )
    assert request.relationships[0].relation_reference.endswith(
        "resources/Account/relations/ownedBy"
    )


@pytest.mark.asyncio
async def test_ingest_records_contact_links_account(ingest):
    service, transport = ingest
    res = await ingest_records(
        "Contact",
        [{"Id": "003C", "Name": "Jane", "Email": "j@x.io", "AccountId": "001A"}],
        ingest=service,
    )
    assert res == {"nodes": 1, "edges": 1}
    request = transport.requests[0]
    contact = next(
        r for r in request.records if r.record_id == "salesforce:Contact:003C"
    )
    # the SDK's persistence privacy guard redacts email-shaped values.
    assert contact.payload["email"] == "[REDACTED_EMAIL]"
    assert request.relationships[0].relation_reference.endswith(
        "resources/Contact/relations/worksAtAccount"
    )


@pytest.mark.asyncio
async def test_ingest_records_opportunity_links_account(ingest):
    service, transport = ingest
    res = await ingest_records(
        "Opportunity",
        [{"Id": "006O", "Name": "Big Deal", "StageName": "Won", "AccountId": "001A"}],
        ingest=service,
    )
    assert res == {"nodes": 1, "edges": 1}
    request = transport.requests[0]
    opp = next(
        r for r in request.records if r.record_id == "salesforce:Opportunity:006O"
    )
    assert opp.payload["stageName"] == "Won"
    assert request.relationships[0].relation_reference.endswith(
        "resources/Opportunity/relations/opportunityForAccount"
    )


def test_map_leads_converted_links():
    entities, rels = map_leads(
        [
            {
                "Id": "00QL",
                "Name": "Prospect",
                "Company": "Acme",
                "Status": "Qualified",
                "ConvertedAccountId": "001A",
                "ConvertedOpportunityId": "006O",
            }
        ]
    )
    assert entities[0]["node_type"] == "Lead"
    assert entities[0]["leadStatus"] == "Qualified"
    rel_types = {r["relationship"] for r in rels}
    assert rel_types == {"convertedToAccount", "convertedToOpportunity"}


@pytest.mark.asyncio
async def test_retired_structural_alias_is_rejected(ingest):
    service, _transport = ingest
    with pytest.raises(IngestError, match="node_type"):
        await ingest_entities([{"id": "a", "type": "Account"}], ingest=service)


@pytest.mark.asyncio
async def test_empty_native_ingest_is_rejected(ingest):
    service, _transport = ingest
    with pytest.raises(IngestError, match="at least one entity"):
        await ingest_entities([], ingest=service)


@pytest.mark.asyncio
async def test_ingest_records_rejects_unknown_sobject(ingest):
    service, _transport = ingest
    with pytest.raises(IngestError, match="unsupported Salesforce object"):
        await ingest_records("Widget", [{"Id": "1"}], ingest=service)


def test_ingest_queries_cover_core_objects():
    assert set(INGEST_QUERIES) == {"Account", "Contact", "Opportunity", "Lead"}
