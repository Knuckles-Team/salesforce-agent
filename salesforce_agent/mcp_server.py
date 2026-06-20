"""Main FastMCP server and tool registration for the Salesforce connector."""

import sys
from typing import Any

from agent_utilities.mcp_utilities import (
    create_mcp_server,
    load_config,
    register_tool_surface,
)
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from salesforce_agent.api_client import Api
from salesforce_agent.auth import get_client
from salesforce_agent.mcp.mcp_salesforce import (
    register_admin_tools,
    register_bulk_tools,
    register_describe_tools,
    register_records_tools,
    register_soql_tools,
)

__version__ = "0.5.0"
logger = get_logger(name="salesforce_agent")


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
        client_cls=Api,
        get_client=get_client,
        service="salesforce-agent",
        registrars=[
            register_soql_tools,
            register_records_tools,
            register_describe_tools,
            register_bulk_tools,
            register_admin_tools,
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
