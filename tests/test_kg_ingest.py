"""Native epistemic-graph typed-node ingestion — Wire-First coverage.

Exercises the real ``ingest_entities`` / ``ingest_records`` seam with a fake engine
client (no engine required), asserting the txn add_node/commit + edge calls and the
Salesforce record → :Account/:Contact/:Opportunity/:Lead (+ :Person owner) mapping.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from salesforce_agent.kg_ingest import (
    INGEST_QUERIES,
    ingest_entities,
    ingest_records,
    map_leads,
)


class _FakeTxn:
    def __init__(self):
        self.nodes = {}
        self.committed = False

    def begin(self, graph=None):
        self.graph = graph
        return "txn-1"

    def add_node(self, txn, node_id, props):
        self.nodes[node_id] = props

    def commit(self, txn):
        self.committed = True
        return True


class _FakeEdges:
    def __init__(self):
        self.edges = []

    def add(self, src, dst, props):
        self.edges.append((src, dst, props))


class _FakeClient:
    def __init__(self):
        self.txn = _FakeTxn()
        self.edges = _FakeEdges()


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "a", "type": "Account", "name": "Acme"},
            {"id": "b", "type": "Contact"},
        ],
        [{"source": "b", "target": "a", "type": "worksAtAccount"}],
        client=c,
        graph="__commons__",
    )
    assert res == {"nodes": 2, "edges": 1}
    assert c.txn.committed is True
    assert set(c.txn.nodes) == {"a", "b"}
    # provenance is stamped
    assert c.txn.nodes["a"]["source"] == "salesforce-agent"
    assert c.txn.nodes["a"]["domain"] == "salesforce"
    assert c.edges.edges == [("b", "a", {"type": "worksAtAccount"})]


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
    assert acct["type"] == "Account"
    assert acct["industry"] == "Tech"
    assert acct["salesforceId"] == "001A"
    assert c.txn.nodes["salesforce:User:005U"]["type"] == "Person"
    assert c.edges.edges == [
        ("salesforce:Account:001A", "salesforce:User:005U", {"type": "ownedBy"})
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
    assert c.edges.edges == [
        (
            "salesforce:Contact:003C",
            "salesforce:Account:001A",
            {"type": "worksAtAccount"},
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
    assert c.edges.edges == [
        (
            "salesforce:Opportunity:006O",
            "salesforce:Account:001A",
            {"type": "opportunityForAccount"},
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
    assert entities[0]["type"] == "Lead"
    assert entities[0]["leadStatus"] == "Qualified"
    rel_types = {r["type"] for r in rels}
    assert rel_types == {"convertedToAccount", "convertedToOpportunity"}


def test_ingest_noops_without_engine():
    # No injected client + no reachable engine -> clean no-op.
    assert ingest_entities([{"id": "a", "type": "Account"}]) is None


def test_ingest_empty_is_noop():
    assert ingest_entities([], client=_FakeClient()) is None
    assert ingest_records("Account", [], client=_FakeClient()) is None


def test_ingest_records_unknown_sobject_is_noop():
    assert ingest_records("Widget", [{"Id": "1"}], client=_FakeClient()) is None


def test_ingest_queries_cover_core_objects():
    assert set(INGEST_QUERIES) == {"Account", "Contact", "Opportunity", "Lead"}
