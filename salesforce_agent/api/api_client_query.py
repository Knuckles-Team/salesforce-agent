"""CONCEPT:SFDC-1.2 SOQL / SOSL query client with auto-pagination.

Resources:
- Query:    https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_query.htm
- QueryAll: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_queryall.htm
- Explain:  https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/dome_query_explain.htm
- Search:   https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_search.htm
"""

from typing import Any

from salesforce_agent.api.api_client_base import ApiClientBase


class QueryClient:
    """SOQL queries (with ``nextRecordsUrl`` pagination) and SOSL search."""

    def __init__(self, base: ApiClientBase):
        self._client = base

    def query(
        self,
        soql: str,
        *,
        query_all: bool = False,
        max_records: int | None = None,
    ) -> dict[str, Any]:
        """Run a SOQL query, following ``nextRecordsUrl`` pages up to a cap.

        ``query_all=True`` uses the ``queryAll`` resource, which includes
        soft-deleted and archived rows. ``max_records`` caps the records
        gathered per call (default: ``SALESFORCE_MAX_QUERY_RECORDS``); when
        the cap stops pagination early the result is flagged ``truncated``
        and carries the unfollowed ``nextRecordsUrl``.
        """
        cap = max_records or self._client.auth.config.max_query_records
        resource = "queryAll" if query_all else "query"
        page = self._client.request(
            "GET", f"{self._client.data_base}/{resource}", params={"q": soql}
        )
        records: list[dict[str, Any]] = list(page.get("records", []))
        while not page.get("done", True) and len(records) < cap:
            page = self._client.request("GET", page["nextRecordsUrl"])
            records.extend(page.get("records", []))

        truncated = len(records) > cap or not page.get("done", True)
        return {
            "totalSize": page.get("totalSize", len(records)),
            "done": page.get("done", True),
            "records": records[:cap],
            "returned": min(len(records), cap),
            "truncated": truncated,
            "nextRecordsUrl": None
            if page.get("done", True)
            else page.get("nextRecordsUrl"),
        }

    def explain(self, soql: str) -> dict[str, Any]:
        """Return the query plan for a SOQL statement (``?explain=``)."""
        return self._client.request(
            "GET", f"{self._client.data_base}/query/", params={"explain": soql}
        )

    def search(self, sosl: str) -> dict[str, Any]:
        """Run a SOSL full-text search (``/search/?q=FIND {...}``)."""
        return self._client.request(
            "GET", f"{self._client.data_base}/search/", params={"q": sosl}
        )
