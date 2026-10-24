"""CONCEPT:AU-ECO.messaging.native-backend-abstraction Unified ecosystem initialization dynamic check."""

from agent_connector_sdk.connector import Connector

from salesforce_agent.mcp_server import _operation_targets

connector = Connector(
    tools="salesforce_agent.mcp_server",
    instructions="Salesforce MCP Server — SOQL/SOSL queries, record CRUD with composite/collections batching, metadata describe, Bulk API 2.0 ingest, and org administration. Destructive operations are gated by SALESFORCE_ALLOW_DESTRUCTIVE.",
    transports=(
        "stdio",
        "streamable-http",
    ),
    verbose_targets=tuple(_operation_targets()),
)
