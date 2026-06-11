"""CONCEPT:SFDC-1.2 Metadata describe, record counts, and org limits client.

Resources:
- Describe Global:  https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_describeGlobal.htm
- sObject Describe: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_sobject_describe.htm
- Record Count:     https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_record_count.htm
- Limits:           https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_limits.htm
"""

from typing import Any

from salesforce_agent.api.api_client_base import ApiClientBase


class DescribeClient:
    """Schema discovery: object lists, field/relationship/picklist metadata."""

    def __init__(self, base: ApiClientBase):
        self._client = base

    def global_describe(self) -> dict[str, Any]:
        """List every sObject available to the integration user."""
        return self._client.request("GET", f"{self._client.data_base}/sobjects")

    def sobject(self, name: str) -> dict[str, Any]:
        """Full describe of one sObject — fields, relationships, picklists."""
        return self._client.request(
            "GET", f"{self._client.data_base}/sobjects/{name}/describe"
        )

    def record_counts(self, sobjects: list[str] | None = None) -> dict[str, Any]:
        """Approximate record counts, optionally for selected sObjects."""
        params = {"sObjects": ",".join(sobjects)} if sobjects else None
        return self._client.request(
            "GET", f"{self._client.data_base}/limits/recordCount", params=params
        )

    def limits(self) -> dict[str, Any]:
        """Org limits and current API usage (DailyApiRequests etc.)."""
        return self._client.request("GET", f"{self._client.data_base}/limits")
