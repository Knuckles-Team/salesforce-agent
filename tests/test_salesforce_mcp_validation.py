"""Action routing through the five MCP tools (in-memory FastMCP client)."""

import json

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

import salesforce_agent.mcp.mcp_salesforce as tools_module
from salesforce_agent.mcp import register_salesforce_tools
from tests.conftest import make_api

EXPECTED_TOOLS = {
    "salesforce_soql",
    "salesforce_records",
    "salesforce_describe",
    "salesforce_bulk",
    "salesforce_admin",
}


@pytest.fixture
def server(fake, monkeypatch):
    mcp = FastMCP("salesforce-test")
    register_salesforce_tools(mcp)
    api = make_api(fake)
    monkeypatch.setattr(tools_module, "get_client", lambda: api)
    yield mcp
    api.close()


@pytest.fixture
def destructive_server(fake, monkeypatch):
    mcp = FastMCP("salesforce-test-destructive")
    register_salesforce_tools(mcp)
    api = make_api(fake, allow_destructive=True)
    monkeypatch.setattr(tools_module, "get_client", lambda: api)
    yield mcp
    api.close()


async def call(server: FastMCP, tool: str, action: str, params: dict | None = None):
    async with Client(server) as client:
        result = await client.call_tool(
            tool, {"action": action, "params_json": json.dumps(params or {})}
        )
    if getattr(result, "data", None) is not None:
        return result.data
    return json.loads(result.content[0].text)


@pytest.mark.concept("SFDC-1.2")
class TestToolInventory:
    async def test_five_action_routed_tools_registered(self, server):
        async with Client(server) as client:
            tools = await client.list_tools()
        assert {t.name for t in tools} == EXPECTED_TOOLS

    async def test_tool_descriptions_enumerate_actions(self, server):
        async with Client(server) as client:
            tools = {t.name: t for t in await client.list_tools()}
        soql_desc = json.dumps(tools["salesforce_soql"].inputSchema)
        for action in ("query", "query_all", "explain", "search"):
            assert action in soql_desc


@pytest.mark.concept("SFDC-1.2")
class TestSoqlTool:
    async def test_query_action(self, fake, server):
        fake.seed_query([{"Id": "1"}, {"Id": "2"}], page_size=10)
        result = await call(
            server, "salesforce_soql", "query", {"soql": "SELECT Id FROM Account"}
        )
        assert result["returned"] == 2

    async def test_query_all_action(self, fake, server):
        fake.seed_query([{"Id": "del"}], page_size=10)
        result = await call(
            server,
            "salesforce_soql",
            "query_all",
            {"soql": "SELECT Id FROM Account"},
        )
        assert result["records"][0]["Id"] == "del"
        assert fake.api_requests[-1].url.path.endswith("/queryAll")

    async def test_search_action(self, fake, server):
        result = await call(
            server, "salesforce_soql", "search", {"sosl": "FIND {Acme}"}
        )
        assert result["searchRecords"]

    async def test_explain_action(self, fake, server):
        result = await call(
            server, "salesforce_soql", "explain", {"soql": "SELECT Id FROM Account"}
        )
        assert "plans" in result

    async def test_unknown_action_rejected(self, server):
        with pytest.raises(ToolError):
            await call(server, "salesforce_soql", "drop_table")


@pytest.mark.concept("SFDC-1.2")
class TestRecordsTool:
    async def test_create_and_get(self, fake, server):
        created = await call(
            server,
            "salesforce_records",
            "create",
            {"sobject": "Account", "data": {"Name": "Acme"}},
        )
        assert created["id"] == "001NEW"
        fetched = await call(
            server,
            "salesforce_records",
            "get",
            {"sobject": "Account", "id": "001NEW", "fields": ["Name"]},
        )
        assert fetched["_requested_fields"] == "Name"

    async def test_upsert_action(self, fake, server):
        result = await call(
            server,
            "salesforce_records",
            "upsert",
            {
                "sobject": "Account",
                "external_id_field": "External_Id__c",
                "external_id": "X-1",
                "data": {"Name": "Acme"},
            },
        )
        assert result["created"] is True

    async def test_composite_action(self, fake, server):
        result = await call(
            server,
            "salesforce_records",
            "composite",
            {
                "subrequests": [
                    {
                        "method": "POST",
                        "url": "/services/data/v62.0/sobjects/Account",
                        "referenceId": "a",
                        "body": {"Name": "Acme"},
                    }
                ]
            },
        )
        assert result["compositeResponse"][0]["referenceId"] == "a"

    async def test_collections_create_action(self, fake, server):
        result = await call(
            server,
            "salesforce_records",
            "collections_create",
            {"records": [{"attributes": {"type": "Account"}, "Name": "Acme"}]},
        )
        assert result[0]["success"] is True


@pytest.mark.concept("SFDC-1.3")
class TestDestructiveGatingThroughTools:
    async def test_delete_blocked(self, fake, server):
        with pytest.raises(ToolError, match="[Bb]locked|SALESFORCE_ALLOW_DESTRUCTIVE"):
            await call(
                server,
                "salesforce_records",
                "delete",
                {"sobject": "Account", "id": "001A"},
            )
        assert fake.api_requests == []

    async def test_bulk_delete_blocked(self, fake, server):
        with pytest.raises(ToolError):
            await call(
                server,
                "salesforce_bulk",
                "create_job",
                {"sobject": "Account", "operation": "delete"},
            )

    async def test_delete_allowed_on_destructive_server(self, fake, destructive_server):
        result = await call(
            destructive_server,
            "salesforce_records",
            "delete",
            {"sobject": "Account", "id": "001A"},
        )
        assert result["success"] is True


@pytest.mark.concept("SFDC-1.2")
class TestDescribeTool:
    async def test_global_action(self, fake, server):
        result = await call(server, "salesforce_describe", "global")
        assert len(result["sobjects"]) == 2

    async def test_sobject_action(self, fake, server):
        result = await call(
            server, "salesforce_describe", "sobject", {"sobject": "Account"}
        )
        assert result["fields"][0]["type"] == "picklist"

    async def test_limits_action(self, fake, server):
        result = await call(server, "salesforce_describe", "limits")
        assert "DailyApiRequests" in result

    async def test_record_counts_action(self, fake, server):
        result = await call(
            server, "salesforce_describe", "record_counts", {"sobjects": ["Contact"]}
        )
        assert result["sObjects"][0]["name"] == "Contact"


@pytest.mark.concept("SFDC-1.4")
class TestBulkTool:
    async def test_lifecycle_through_tool(self, fake, server):
        job = await call(
            server,
            "salesforce_bulk",
            "create_job",
            {"sobject": "Account", "operation": "insert"},
        )
        await call(
            server,
            "salesforce_bulk",
            "upload",
            {"job_id": job["id"], "csv": "Name\nAcme"},
        )
        closed = await call(server, "salesforce_bulk", "close", {"job_id": job["id"]})
        assert closed["state"] == "JobComplete"
        results = await call(
            server,
            "salesforce_bulk",
            "results",
            {"job_id": job["id"], "kind": "successful", "max_bytes": 10},
        )
        assert results["truncated"] is True

    async def test_list_jobs_action(self, fake, server):
        listing = await call(server, "salesforce_bulk", "list_jobs")
        assert listing["records"] == []


@pytest.mark.concept("SFDC-1.2")
class TestAdminTool:
    async def test_user_info_action(self, fake, server):
        result = await call(server, "salesforce_admin", "user_info")
        assert result["user_id"].startswith("005")

    async def test_run_report_action(self, fake, server):
        result = await call(
            server, "salesforce_admin", "run_report", {"report_id": "00O1"}
        )
        assert result["allData"] is True

    async def test_flows_note_in_description(self, server):
        async with Client(server) as client:
            tools = {t.name: t for t in await client.list_tools()}
        assert "OUT of scope" in json.dumps(tools["salesforce_admin"].inputSchema)


@pytest.mark.concept("SFDC-1.2")
@pytest.mark.parametrize(
    "tool",
    sorted(EXPECTED_TOOLS),
)
async def test_every_tool_rejects_unknown_actions(server, tool):
    with pytest.raises(ToolError):
        await call(server, tool, "definitely_not_an_action")
