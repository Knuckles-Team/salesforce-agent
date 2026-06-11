"""Salesforce REST API resource clients (owned thin httpx wrappers)."""

from salesforce_agent.api.api_client_admin import AdminClient
from salesforce_agent.api.api_client_base import ApiClientBase
from salesforce_agent.api.api_client_bulk import BulkClient
from salesforce_agent.api.api_client_describe import DescribeClient
from salesforce_agent.api.api_client_query import QueryClient
from salesforce_agent.api.api_client_records import RecordsClient

__all__ = [
    "AdminClient",
    "ApiClientBase",
    "BulkClient",
    "DescribeClient",
    "QueryClient",
    "RecordsClient",
]
