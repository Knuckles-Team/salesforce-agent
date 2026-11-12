"""One typed tool per operation, served through the connector (in-memory FastMCP client)."""

import json
from unittest.mock import patch

import pytest
from fastmcp import Client
from scion_sdk.connector import build_server

import salesforce_agent.mcp.mcp_salesforce as tools_module
import salesforce_agent.mcp_server as server_module
from tests.conftest import make_api

OPERATION_TOOLS = {
    "salesforce_soql_query",
    "salesforce_soql_explain",
    "salesforce_soql_search",
    "salesforce_records_get",
    "salesforce_records_create",
    "salesforce_records_update",
    "salesforce_records_upsert",
    "salesforce_records_delete",
    "salesforce_records_composite",
    "salesforce_records_collections_create",
    "salesforce_records_collections_update",
    "salesforce_records_collections_delete",
    "salesforce_describe_global_describe",
    "salesforce_describe_sobject",
    "salesforce_describe_record_counts",
    "salesforce_describe_limits",
    "salesforce_bulk_create_ingest_job",
    "salesforce_bulk_upload",
    "salesforce_bulk_close",
    "salesforce_bulk_abort",
    "salesforce_bulk_status",
    "salesforce_bulk_list_jobs",
    "salesforce_bulk_delete_job",
    "salesforce_bulk_results",
    "salesforce_admin_user_info",
    "salesforce_admin_org_info",
    "salesforce_admin_list_reports",
    "salesforce_admin_run_report",
}
ACTION_ROUTED = {
    "salesforce_soql",
    "salesforce_records",
    "salesforce_describe",
    "salesforce_bulk",
    "salesforce_admin",
}


def _build():
    with (
        patch.dict(
            "os.environ",
            {"SALESFORCE_INSTANCE_URL": "https://example.my.salesforce.com"},
        ),
        patch("sys.argv", ["salesforce-mcp"]),
    ):
        return build_server("salesforce_agent", command_args=[])[1]


def _wire(monkeypatch, api):
    monkeypatch.setattr(tools_module, "get_client", lambda: api)
    monkeypatch.setattr(server_module, "get_client", lambda: api)


@pytest.fixture
def server(fake, monkeypatch):
    api = make_api(fake)
    _wire(monkeypatch, api)
    yield _build()
    api.close()


async def call(server, tool: str, params: dict | None = None):
    async with Client(server) as client:
        result = await client.call_tool(tool, params or {})
    if getattr(result, "data", None) is not None:
        return result.data
    return json.loads(result.content[0].text)


@pytest.mark.concept("SFDC-1.2")
class TestToolInventory:
    async def test_every_operation_is_a_typed_tool(self, server):
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
        assert OPERATION_TOOLS <= names
        assert "salesforce_ingest_crm" in names

    async def test_no_action_routed_tool_is_served(self, server):
        async with Client(server) as client:
            tools = await client.list_tools()
        assert not ACTION_ROUTED & {t.name for t in tools}
        for tool in tools:
            assert "action" not in (tool.inputSchema.get("properties") or {})


@pytest.mark.concept("SFDC-1.2")
class TestSoqlTools:
    async def test_query(self, fake, server):
        fake.seed_query([{"Id": "1"}, {"Id": "2"}], page_size=10)
        result = await call(
            server, "salesforce_soql_query", {"soql": "SELECT Id FROM Account"}
        )
        assert result["returned"] == 2

    async def test_query_all(self, fake, server):
        fake.seed_query([{"Id": "del"}], page_size=10)
        result = await call(
            server,
            "salesforce_soql_query",
            {"soql": "SELECT Id FROM Account", "query_all": True},
        )
        assert result["records"][0]["Id"] == "del"
        assert fake.api_requests[-1].url.path.endswith("/queryAll")

    async def test_search(self, fake, server):
        result = await call(server, "salesforce_soql_search", {"sosl": "FIND {Acme}"})
        assert result["searchRecords"]

    async def test_explain(self, fake, server):
        result = await call(
            server, "salesforce_soql_explain", {"soql": "SELECT Id FROM Account"}
        )
        assert "plans" in result


@pytest.mark.concept("SFDC-1.2")
class TestRecordTools:
    async def test_create_and_get(self, fake, server):
        created = await call(
            server,
            "salesforce_records_create",
            {"sobject": "Account", "data": {"Name": "Acme"}},
        )
        assert created["id"] == "001NEW"
        fetched = await call(
            server,
            "salesforce_records_get",
            {"sobject": "Account", "record_id": "001NEW", "fields": ["Name"]},
        )
        assert fetched["_requested_fields"] == "Name"

    async def test_upsert(self, fake, server):
        result = await call(
            server,
            "salesforce_records_upsert",
            {
                "sobject": "Account",
                "external_id_field": "External_Id__c",
                "external_id": "X-1",
                "data": {"Name": "Acme"},
            },
        )
        assert result["created"] is True

    async def test_composite(self, fake, server):
        result = await call(
            server,
            "salesforce_records_composite",
            {
                "subrequests": [
                    {
                        "method": "POST",
                        "url": "/services/data/v62.0/sobjects/Account",
                        "referenceId": "a",
                        "body": {"Name": "Acme"},
                    }
                ],
                "confirm": True,
            },
        )
        assert result["compositeResponse"][0]["referenceId"] == "a"

    async def test_collections_create(self, fake, server):
        result = await call(
            server,
            "salesforce_records_collections_create",
            {"records": [{"attributes": {"type": "Account"}, "Name": "Acme"}]},
        )
        assert result[0]["success"] is True


@pytest.mark.concept("SFDC-1.3")
class TestDestructiveGatingThroughTools:
    async def test_delete_without_confirmation_is_refused(self, fake, server):
        result = await call(
            server,
            "salesforce_records_delete",
            {"sobject": "Account", "record_id": "001A"},
        )
        assert result["cancelled"] is True
        assert fake.api_requests == []

    @pytest.mark.spec("CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R004")
    async def test_declared_operations_are_destructive_tools_that_ask_first(
        self, fake, server
    ):
        async with Client(server) as client:
            tools = {t.name: t for t in await client.list_tools()}
        declared = {
            "salesforce_records_delete",
            "salesforce_records_collections_delete",
            "salesforce_records_composite",
            "salesforce_bulk_create_ingest_job",
        }
        for name in declared:
            assert tools[name].annotations.destructive_hint is True, name
            assert "confirm" in tools[name].input_schema["properties"], name
        for name, tool in tools.items():
            assert "allow_destructive" not in tool.input_schema["properties"], name
        for name, arguments in (
            ("salesforce_records_composite", {"subrequests": []}),
            (
                "salesforce_bulk_create_ingest_job",
                {"sobject": "Account", "operation": "delete"},
            ),
            (
                "salesforce_records_collections_delete",
                {"ids": ["001A"]},
            ),
        ):
            refused = await call(server, name, arguments)
            assert refused["cancelled"] is True, name
        assert fake.api_requests == []

    async def test_confirmed_delete_runs_on_server(self, fake, server):
        result = await call(
            server,
            "salesforce_records_delete",
            {"sobject": "Account", "record_id": "001A", "confirm": True},
        )
        assert result["success"] is True


@pytest.mark.concept("SFDC-1.2")
class TestDescribeTools:
    async def test_global(self, fake, server):
        result = await call(server, "salesforce_describe_global_describe")
        assert len(result["sobjects"]) == 2

    async def test_sobject(self, fake, server):
        result = await call(server, "salesforce_describe_sobject", {"name": "Account"})
        assert result["fields"][0]["type"] == "picklist"

    async def test_limits(self, fake, server):
        result = await call(server, "salesforce_describe_limits")
        assert "DailyApiRequests" in result

    async def test_record_counts(self, fake, server):
        result = await call(
            server, "salesforce_describe_record_counts", {"sobjects": ["Contact"]}
        )
        assert result["sObjects"][0]["name"] == "Contact"


@pytest.mark.concept("SFDC-1.4")
class TestBulkTools:
    async def test_lifecycle_through_tools(self, fake, server):
        job = await call(
            server,
            "salesforce_bulk_create_ingest_job",
            {"sobject": "Account", "operation": "insert", "confirm": True},
        )
        await call(
            server,
            "salesforce_bulk_upload",
            {"job_id": job["id"], "csv_data": "Name\nAcme"},
        )
        closed = await call(server, "salesforce_bulk_close", {"job_id": job["id"]})
        assert closed["state"] == "JobComplete"
        results = await call(
            server,
            "salesforce_bulk_results",
            {"job_id": job["id"], "kind": "successful", "max_bytes": 10},
        )
        assert results["truncated"] is True

    async def test_list_jobs(self, fake, server):
        listing = await call(server, "salesforce_bulk_list_jobs")
        assert listing["records"] == []


@pytest.mark.concept("SFDC-1.2")
class TestAdminTools:
    async def test_user_info(self, fake, server):
        result = await call(server, "salesforce_admin_user_info")
        assert result["user_id"].startswith("005")

    async def test_run_report(self, fake, server):
        result = await call(
            server, "salesforce_admin_run_report", {"report_id": "00O1"}
        )
        assert result["allData"] is True
