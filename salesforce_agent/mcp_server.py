"""Main FastMCP server and tool registration for the Salesforce connector."""

import sys
from typing import Any

from agent_connector_sdk.config import load_config
from agent_connector_sdk.mcp.server import create_mcp_server
from agent_connector_sdk.mcp.tool_surface import register_tool_surface
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from salesforce_agent.api import (
    AdminClient,
    BulkClient,
    DescribeClient,
    QueryClient,
    RecordsClient,
)
from salesforce_agent.auth import get_client
from salesforce_agent.mcp.mcp_salesforce import (
    register_admin_tools,
    register_bulk_tools,
    register_describe_tools,
    register_ingest_tools,
    register_records_tools,
    register_soql_tools,
)

__version__ = "2.3.0"
logger = get_logger(name="salesforce_agent")


def _operation_targets() -> list[dict[str, Any]]:
    """One operation-tool group per resource client of the ``Api`` facade."""
    resources = {
        "soql": QueryClient,
        "records": RecordsClient,
        "describe": DescribeClient,
        "bulk": BulkClient,
        "admin": AdminClient,
    }
    return [
        {
            "client_cls": client_cls,
            "get_client": (lambda name=name: getattr(get_client(), name)),
            "prefix": f"salesforce_{name}",
        }
        for name, client_cls in resources.items()
    ]


def get_mcp_instance() -> tuple[Any, ...]:
    load_config()
    args, mcp, middlewares = create_mcp_server(
        name="Salesforce MCP",
        version=__version__,
        instructions=(
            "Salesforce MCP Server — SOQL/SOSL queries, record CRUD with "
            "composite/collections batching, metadata describe, Bulk API "
            "2.0 ingest, and org administration. Destructive operations are "
            "gated by SALESFORCE_ALLOW_DESTRUCTIVE."
        ),
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse({"status": "OK"})

    register_tool_surface(
        mcp,
        service="salesforce-agent",
        verbose_targets=_operation_targets(),
        registrars=[
            register_soql_tools,
            register_records_tools,
            register_describe_tools,
            register_bulk_tools,
            register_admin_tools,
            register_ingest_tools,
        ],
    )

    for mw in middlewares:
        mcp.add_middleware(mw)
    return mcp, args, middlewares


def mcp_server() -> None:
    mcp, args, middlewares = get_mcp_instance()
    print(f"Salesforce MCP v{__version__}", file=sys.stderr)
    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    mcp_server()
