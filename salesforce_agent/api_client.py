"""CONCEPT:SFDC-1.0 Salesforce API facade — one client, five surfaces.

``Api`` wires the auth/token layer and the shared httpx base into the five
resource clients (``soql``, ``records``, ``describe``, ``bulk``, ``admin``).
Pass ``transport`` (an ``httpx.BaseTransport``) to route both token and API
traffic through a mock in tests.
"""

import httpx

from salesforce_agent.api import (
    AdminClient,
    ApiClientBase,
    BulkClient,
    DescribeClient,
    QueryClient,
    RecordsClient,
)
from salesforce_agent.auth import SalesforceAuth, SalesforceConfig


class Api:
    """Configured Salesforce connection facade."""

    def __init__(
        self,
        config: SalesforceConfig | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.config = config or SalesforceConfig.from_env()
        self.auth = SalesforceAuth(self.config, transport=transport)
        self._base = ApiClientBase(self.auth, transport=transport)
        self.soql = QueryClient(self._base)
        self.records = RecordsClient(self._base)
        self.describe = DescribeClient(self._base)
        self.bulk = BulkClient(self._base)
        self.admin = AdminClient(self._base)

    def close(self) -> None:
        self._base.close()
        self.auth.close()

    def __enter__(self) -> "Api":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
