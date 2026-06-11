"""MCP tool registration modules for the Salesforce connector."""

from salesforce_agent.mcp.mcp_salesforce import (
    register_admin_tools,
    register_bulk_tools,
    register_describe_tools,
    register_records_tools,
    register_salesforce_tools,
    register_soql_tools,
)

__all__ = [
    "register_admin_tools",
    "register_bulk_tools",
    "register_describe_tools",
    "register_records_tools",
    "register_salesforce_tools",
    "register_soql_tools",
]
