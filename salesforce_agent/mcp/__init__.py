"""MCP tool registration modules for the Salesforce connector."""

from salesforce_agent.mcp.mcp_salesforce import (
    register_ingest_tools,
    register_salesforce_tools,
)

__all__ = ["register_ingest_tools", "register_salesforce_tools"]
