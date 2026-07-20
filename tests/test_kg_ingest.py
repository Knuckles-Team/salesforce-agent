"""Native epistemic-graph typed-node ingestion — Wire-First coverage.

Exercises the real ``ingest_entities`` / ``ingest_records`` seam with a fake engine
client (no engine required), asserting the txn add_node/commit + edge calls and the
Salesforce record → :Account/:Contact/:Opportunity/:Lead (+ :Person owner) mapping.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

import pytest
from agent_utilities.knowledge_graph.memory.native_ingest import NativeIngestError

from salesforce_agent.kg_ingest import (
    INGEST_QUERIES,
    ingest_entities,
    ingest_records,
    map_leads,
)


class _FakeTxn:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.committed = False

    def begin(self, graph=None):
        self.graph = graph
        return "txn-1"

    def add_node(self, txn, node_id, props):
        self.nodes[node_id] = props

    def add_edge(self, txn, source, target, props):
        self.edges.append((source, target, props))

    def commit(self, txn):
        self.committed = True
        return True


class _FakeClient:
    def __init__(self):
        self.txn = _FakeTxn()


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "a", "node_type": "Account", "name": "Acme"},
            {"id": "b", "node_type": "Contact"},
        ],
        [{"source": "b", "target": "a", "relationship": "worksAtAccount"}],
        client=c,
        graph="__commons__",
    )
    assert res == {"nodes": 2, "edges": 1}
    assert c.txn.committed is True
    assert set(c.txn.nodes) == {"a", "b"}
    # provenance is stamped
    assert c.txn.nodes["a"]["source"] == "salesforce-agent"
    assert c.txn.nodes["a"]["domain"] == "salesforce"
    assert c.txn.edges == [("b", "a", {"relationship": "worksAtAccount"})]


def test_ingest_records_accounts_with_owner():
    c = _FakeClient()
    res = ingest_records(
        "Account",
        [{"Id": "001A", "Name": "Acme", "Industry": "Tech", "OwnerId": "005U"}],
        client=c,
        graph="__commons__",
    )
    # 1 account + 1 owner Person node, 1 ownedBy edge
    assert res == {"nodes": 2, "edges": 1}
    acct = c.txn.nodes["salesforce:Account:001A"]
    assert acct["node_type"] == "Account"
    assert acct["industry"] == "Tech"
    assert acct["salesforceId"] == "001A"
    assert c.txn.nodes["salesforce:User:005U"]["node_type"] == "Person"
    assert c.txn.edges == [
        ("salesforce:Account:001A", "salesforce:User:005U", {"relationship": "ownedBy"})
    ]


def test_ingest_records_contact_links_account():
    c = _FakeClient()
    res = ingest_records(
        "Contact",
        [{"Id": "003C", "Name": "Jane", "Email": "j@x.io", "AccountId": "001A"}],
        client=c,
        graph="__commons__",
    )
    assert res == {"nodes": 1, "edges": 1}
    assert c.txn.nodes["salesforce:Contact:003C"]["email"] == "j@x.io"
    assert c.txn.edges == [
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
        graph="__commons__",
    )
    assert res == {"nodes": 1, "edges": 1}
    opp = c.txn.nodes["salesforce:Opportunity:006O"]
    assert opp["stageName"] == "Won"
    assert c.txn.edges == [
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
