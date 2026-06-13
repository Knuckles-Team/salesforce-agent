"""Main FastMCP server and tool registration for the Salesforce connector."""

import os
import sys
from typing import Any

from agent_utilities.base_utilities import to_boolean
from agent_utilities.mcp_utilities import create_mcp_server
from dotenv import find_dotenv, load_dotenv
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from salesforce_agent.mcp.mcp_salesforce import (
    register_admin_tools,
    register_bulk_tools,
    register_describe_tools,
    register_records_tools,
    register_soql_tools,
)

__version__ = "0.3.0"
logger = get_logger(name="salesforce_agent")

DEFAULT_SOQLTOOL = to_boolean(os.getenv("SOQLTOOL", "True"))
DEFAULT_RECORDSTOOL = to_boolean(os.getenv("RECORDSTOOL", "True"))
DEFAULT_DESCRIBETOOL = to_boolean(os.getenv("DESCRIBETOOL", "True"))
DEFAULT_BULKTOOL = to_boolean(os.getenv("BULKTOOL", "True"))
DEFAULT_ADMINTOOL = to_boolean(os.getenv("ADMINTOOL", "True"))


def get_mcp_instance() -> tuple[Any, ...]:
    load_dotenv(find_dotenv())
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

    if DEFAULT_SOQLTOOL:
        register_soql_tools(mcp)
    if DEFAULT_RECORDSTOOL:
        register_records_tools(mcp)
    if DEFAULT_DESCRIBETOOL:
        register_describe_tools(mcp)
    if DEFAULT_BULKTOOL:
        register_bulk_tools(mcp)
    if DEFAULT_ADMINTOOL:
        register_admin_tools(mcp)

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
