"""SOQL pagination/caps, queryAll, explain, and SOSL search."""

import pytest

SOQL = "SELECT Id FROM Account"


@pytest.mark.concept("SFDC-1.2")
class TestQueryPagination:
    def test_single_page(self, fake, api):
        fake.seed_query([{"Id": "1"}], page_size=10)
        result = api.soql.query(SOQL)
        assert result["records"] == [{"Id": "1"}]
        assert result["done"] is True
        assert result["truncated"] is False
        assert result["nextRecordsUrl"] is None

    def test_follows_next_records_url(self, fake, api):
        fake.seed_query([{"Id": str(i)} for i in range(5)], page_size=2)
        result = api.soql.query(SOQL)
        assert [r["Id"] for r in result["records"]] == ["0", "1", "2", "3", "4"]
        assert result["returned"] == 5
        assert result["totalSize"] == 5
        assert result["truncated"] is False
        # 1 initial + 2 follow-up pages
        query_calls = [r for r in fake.api_requests if "/query" in r.url.path]
        assert len(query_calls) == 3

    def test_cap_stops_pagination(self, fake, api):
        fake.seed_query([{"Id": str(i)} for i in range(10)], page_size=2)
        result = api.soql.query(SOQL, max_records=4)
        assert result["returned"] == 4
        assert result["truncated"] is True
        assert result["nextRecordsUrl"] is not None
        query_calls = [r for r in fake.api_requests if "/query" in r.url.path]
        assert len(query_calls) == 2  # stopped early

    def test_cap_trims_oversized_page(self, fake, api):
        fake.seed_query([{"Id": str(i)} for i in range(5)], page_size=5)
        result = api.soql.query(SOQL, max_records=3)
        assert result["returned"] == 3
        assert result["truncated"] is True

    def test_default_cap_from_config(self, fake):
        from tests.conftest import make_api

        client = make_api(fake, max_query_records=2)
        fake.seed_query([{"Id": str(i)} for i in range(6)], page_size=2)
        result = client.soql.query(SOQL)
        assert result["returned"] == 2
        assert result["truncated"] is True
        client.close()

    def test_query_sends_soql_param(self, fake, api):
        fake.seed_query([], page_size=2)
        api.soql.query(SOQL)
        request = fake.api_requests[-1]
        assert request.url.params["q"] == SOQL
        assert request.url.path.endswith("/query")


@pytest.mark.concept("SFDC-1.2")
class TestQueryAll:
    def test_uses_query_all_resource(self, fake, api):
        fake.seed_query([{"Id": "del-1", "IsDeleted": True}], page_size=10)
        result = api.soql.query(SOQL, query_all=True)
        assert result["records"][0]["IsDeleted"] is True
        assert fake.api_requests[-1].url.path.endswith("/queryAll")


@pytest.mark.concept("SFDC-1.2")
class TestExplainAndSearch:
    def test_explain(self, fake, api):
        plans = api.soql.explain(SOQL)
        assert plans["plans"][0]["leadingOperationType"] == "Index"
        assert fake.api_requests[-1].url.params["explain"] == SOQL

    def test_sosl_search(self, fake, api):
        sosl = "FIND {Acme} IN ALL FIELDS RETURNING Account(Id)"
        result = api.soql.search(sosl)
        assert result["searchRecords"][0]["Id"] == "001A"
        assert fake.api_requests[-1].url.params["q"] == sosl
