"""CONCEPT:SFDC-1.2 Org administration: identity, org info, and analytics.

Resources:
- UserInfo (OIDC): https://help.salesforce.com/s/articleView?id=sf.remoteaccess_using_userinfo_endpoint.htm
- Reports REST:    https://developer.salesforce.com/docs/atlas.en-us.api_analytics.meta/api_analytics/sforce_analytics_rest_api_intro.htm

Flows (list/run via the Actions or Tooling APIs) are intentionally OUT of
scope for v1 of this connector — running flows mutates org state through an
API surface with weaker guardrails; revisit behind ``allow_destructive``.
"""

from typing import Any

from salesforce_agent.api.api_client_base import ApiClientBase

ORG_INFO_SOQL = (
    "SELECT Id, Name, OrganizationType, IsSandbox, InstanceName, "
    "LanguageLocaleKey, TrialExpirationDate FROM Organization"
)


class AdminClient:
    """Current user/org identity plus the synchronous Reports REST surface."""

    def __init__(self, base: ApiClientBase):
        self._client = base

    def user_info(self) -> dict[str, Any]:
        """Identity of the integration user (``/services/oauth2/userinfo``)."""
        return self._client.request("GET", "/services/oauth2/userinfo")

    def org_info(self) -> dict[str, Any]:
        """Organization record (name, type, sandbox flag, instance)."""
        return self._client.request(
            "GET",
            f"{self._client.data_base}/query",
            params={"q": ORG_INFO_SOQL},
        )

    def list_reports(self) -> Any:
        """Recently viewed reports (``/analytics/reports`` list resource)."""
        return self._client.request(
            "GET", f"{self._client.data_base}/analytics/reports"
        )

    def run_report(
        self, report_id: str, include_details: bool = True
    ) -> dict[str, Any]:
        """Run a report synchronously.

        Salesforce caps synchronous report results at 2,000 detail rows —
        results beyond the cap are dropped by the platform, not paged.
        """
        return self._client.request(
            "GET",
            f"{self._client.data_base}/analytics/reports/{report_id}",
            params={"includeDetails": str(include_details).lower()},
        )
