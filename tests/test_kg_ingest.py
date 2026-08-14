"""Native epistemic-graph typed-node ingestion — Wire-First coverage.

Exercises the real ``ingest_entities`` / ``ingest_records`` seam with a fake engine
client (no engine required), asserting the txn add_node/commit + edge calls and the
Salesforce record → :Account/:Contact/:Opportunity/:Lead (+ :Person owner) mapping.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from typing import Any

import msgpack
import pytest
from agent_utilities.knowledge_graph.memory.native_ingest import NativeIngestError
from agent_utilities.security.brain_context import ActorContext, use_actor
from agent_utilities.models.company_brain import ActorType
from agent_utilities.knowledge_graph.core.session import GraphSession, use_session

from salesforce_agent.kg_ingest import (
    INGEST_QUERIES,
    ingest_entities,
    ingest_records,
    map_leads,
)


@pytest.fixture(autouse=True)
def _governed_session():
    actor = ActorContext(
        actor_id="subject:opaque:synthetic",
        actor_type=ActorType.AUTOMATED_SERVICE,
        roles=(),
        tenant_id="tenant:opaque:synthetic",
        authenticated=True,
    )
    session = GraphSession(
        actor=actor,
        tenant=actor.tenant_id,
        scopes=frozenset({"kg:write"}),
        graph="graph:opaque:synthetic",
        policy_version="policy:opaque:synthetic",
        audience="epistemic-graph",
    )
    with use_actor(actor), use_session(session):
        yield


class _FakeNodes:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, Any]] = {}

    def properties(self, node_id: str) -> dict[str, Any] | None:
        return self.values.get(node_id)

    def list(self) -> list[tuple[str, dict[str, Any]]]:
        return list(self.values.items())


class _FakeChanges:
    def __init__(self, nodes: _FakeNodes) -> None:
        self.nodes = nodes
        self.edges: list[tuple[str, str, dict[str, Any]]] = []
        self.applied: list[dict[str, Any]] = []
        self.records: dict[str, dict[str, Any]] = {}
        self.versions: dict[str, dict[str, Any]] = {}

    def get(self, envelope_id: str) -> dict[str, Any] | None:
        return self.records.get(envelope_id)

    def content_version(self, object_id: str) -> dict[str, Any] | None:
        return self.versions.get(object_id)

    def cursor(self, _source: str, _partition: str = "") -> None:
        return None

    def apply(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self.applied.append(envelope)
        mutation = envelope["mutation"]
        for operation in mutation["operations"]:
            method = operation["method"]
            params = method["params"]
            properties = msgpack.unpackb(params["properties_msgpack"], raw=False)
            if method["method"] == "AddNode":
                self.nodes.values[params["node_id"]] = properties
            elif method["method"] == "AddEdge":
                self.edges.append(
                    (params["source_id"], params["target_id"], properties)
                )
        version = envelope["content_version"]
        self.versions[version["object_id"]] = version
        self.records[envelope["envelope_id"]] = envelope
        return {
            "batch_id": mutation["batch_id"],
            "replayed": False,
            "projection_pending": False,
        }


class _FakeRdf:
    def validate_shacl(self, _shapes: str, _data_graph: str) -> dict[str, Any]:
        return {"conforms": True, "results": []}


class _FakeClient:
    def __init__(self) -> None:
        self.nodes = _FakeNodes()
        self.changes = _FakeChanges(self.nodes)
        self.rdf = _FakeRdf()

    @staticmethod
    def supports(operation: str) -> bool:
        return operation == "ApplyChangeEnvelope"


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "a", "node_type": "Account", "name": "Acme"},
            {"id": "b", "node_type": "Contact"},
        ],
        [{"source": "b", "target": "a", "relationship": "worksAtAccount"}],
        client=c,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert len(c.changes.applied) == 1
    assert set(c.nodes.values) == {"a", "b"}
    # provenance is stamped
    assert c.nodes.values["a"]["source"] == "salesforce-agent"
    assert c.nodes.values["a"]["domain"] == "salesforce"
    assert c.changes.edges == [("b", "a", {"relationship": "worksAtAccount"})]


def test_ingest_records_accounts_with_owner():
    c = _FakeClient()
    res = ingest_records(
        "Account",
        [{"Id": "001A", "Name": "Acme", "Industry": "Tech", "OwnerId": "005U"}],
        client=c,
    )
    # 1 account + 1 owner Person node, 1 ownedBy edge
    assert res == {"nodes": 2, "edges": 1}
    acct = c.nodes.values["salesforce:Account:001A"]
    assert acct["node_type"] == "Account"
    assert acct["industry"] == "Tech"
    assert acct["salesforceId"] == "001A"
    assert c.nodes.values["salesforce:User:005U"]["node_type"] == "Person"
    assert c.changes.edges == [
        ("salesforce:Account:001A", "salesforce:User:005U", {"relationship": "ownedBy"})
    ]


def test_ingest_records_contact_links_account():
    c = _FakeClient()
    res = ingest_records(
        "Contact",
        [{"Id": "003C", "Name": "Jane", "Email": "j@x.io", "AccountId": "001A"}],
        client=c,
    )
    assert res == {"nodes": 1, "edges": 1}
    # native_ingest's governed PII scrubber redacts email-shaped values.
    assert c.nodes.values["salesforce:Contact:003C"]["email"] == "[REDACTED_EMAIL]"
    assert c.changes.edges == [
        (
            "salesforce:Contact:003C",
            "salesforce:Account:001A",
            {"relationship": "worksAtAccount"},
        )
    ]


def test_ingest_records_opportunity_links_account():
    c = _FakeClient()
    res = ingest_records(
        "Opportunity",
        [{"Id": "006O", "Name": "Big Deal", "StageName": "Won", "AccountId": "001A"}],
        client=c,
    )
    assert res == {"nodes": 1, "edges": 1}
    opp = c.nodes.values["salesforce:Opportunity:006O"]
    assert opp["stageName"] == "Won"
    assert c.changes.edges == [
        (
            "salesforce:Opportunity:006O",
            "salesforce:Account:001A",
            {"relationship": "opportunityForAccount"},
        )
    ]


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


def test_retired_structural_alias_is_rejected():
    with pytest.raises(NativeIngestError, match="canonical node_type"):
        ingest_entities([{"id": "a", "type": "Account"}], client=_FakeClient())


def test_empty_native_ingest_is_rejected():
    with pytest.raises(NativeIngestError, match="at least one entity"):
        ingest_entities([], client=_FakeClient())


def test_ingest_records_rejects_unknown_sobject():
    with pytest.raises(NativeIngestError, match="unsupported Salesforce object"):
        ingest_records("Widget", [{"Id": "1"}], client=_FakeClient())


def test_ingest_queries_cover_core_objects():
    assert set(INGEST_QUERIES) == {"Account", "Contact", "Opportunity", "Lead"}
