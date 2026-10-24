"""Main FastMCP server and tool registration for the Salesforce connector."""

from typing import Any

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

# SDK discovery registers the register_<tag>_tools functions bound in this module.
__all__ = [
    "register_admin_tools",
    "register_bulk_tools",
    "register_describe_tools",
    "register_ingest_tools",
    "register_records_tools",
    "register_soql_tools",
]


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
