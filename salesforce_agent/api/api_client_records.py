"""CONCEPT:SFDC-1.2 sObject record CRUD, composite, and collections client.

Resources:
- sObject rows:    https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_sobject_retrieve.htm
- Upsert:          https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/dome_upsert.htm
- Composite:       https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_composite_composite.htm
- Collections:     https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_composite_sobjects_collections.htm

CONCEPT:SFDC-1.3 — destructive operations (delete / collections delete, and
DELETE subrequests inside composite) are refused unless
``allow_destructive`` is enabled.
"""

from typing import Any

from salesforce_agent.api.api_client_base import ApiClientBase
from salesforce_agent.salesforce_response_models import (
    DestructiveOperationBlockedError,
    SalesforceBadRequestError,
)

COMPOSITE_MAX_SUBREQUESTS = 25
COLLECTIONS_MAX_RECORDS = 200


class RecordsClient:
    """Single-record CRUD plus composite (25) and collections (200) batching."""

    def __init__(self, base: ApiClientBase):
        self._client = base

    def _guard_destructive(self, operation: str) -> None:
        if not self._client.auth.config.allow_destructive:
            raise DestructiveOperationBlockedError(operation)

    # ------------------------------------------------------------------ #
    # Single-record CRUD
    # ------------------------------------------------------------------ #
    def get(
        self,
        sobject: str,
        record_id: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retrieve one record, optionally restricted to selected fields."""
        params = {"fields": ",".join(fields)} if fields else None
        return self._client.request(
            "GET",
            f"{self._client.data_base}/sobjects/{sobject}/{record_id}",
            params=params,
        )

    def create(self, sobject: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a record; returns ``{"id": ..., "success": true}``."""
        return self._client.request(
            "POST", f"{self._client.data_base}/sobjects/{sobject}", json=data
        )

    def update(
        self, sobject: str, record_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update fields on a record (PATCH; Salesforce answers 204)."""
        return self._client.request(
            "PATCH",
            f"{self._client.data_base}/sobjects/{sobject}/{record_id}",
            json=data,
        )

    def upsert(
        self,
        sobject: str,
        external_id_field: str,
        external_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create-or-update a record addressed by an external-id field."""
        return self._client.request(
            "PATCH",
            f"{self._client.data_base}/sobjects/{sobject}"
            f"/{external_id_field}/{external_id}",
            json=data,
        )

    def delete(self, sobject: str, record_id: str) -> dict[str, Any]:
        """Delete one record. Gated by ``allow_destructive``."""
        self._guard_destructive("records.delete")
        return self._client.request(
            "DELETE", f"{self._client.data_base}/sobjects/{sobject}/{record_id}"
        )

    # ------------------------------------------------------------------ #
    # Composite (heterogeneous, up to 25 subrequests)
    # ------------------------------------------------------------------ #
    def composite(
        self,
        subrequests: list[dict[str, Any]],
        all_or_none: bool = False,
    ) -> dict[str, Any]:
        """Run up to 25 dependent subrequests in one ``/composite`` call.

        Each subrequest needs ``method``, ``url``, ``referenceId`` (and
        ``body`` for writes). DELETE subrequests are gated by
        ``allow_destructive``.
        """
        if not subrequests:
            raise SalesforceBadRequestError("composite needs at least one subrequest.")
        if len(subrequests) > COMPOSITE_MAX_SUBREQUESTS:
            raise SalesforceBadRequestError(
                f"composite accepts at most {COMPOSITE_MAX_SUBREQUESTS} "
                f"subrequests, got {len(subrequests)}."
            )
        for sub in subrequests:
            if str(sub.get("method", "")).upper() == "DELETE":
                self._guard_destructive("records.composite[DELETE]")
        return self._client.request(
            "POST",
            f"{self._client.data_base}/composite",
            json={"allOrNone": all_or_none, "compositeRequest": subrequests},
        )

    # ------------------------------------------------------------------ #
    # sObject collections (homogeneous verb, up to 200 records)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _check_collection_size(count: int, what: str) -> None:
        if count == 0:
            raise SalesforceBadRequestError(f"collections {what} got no records.")
        if count > COLLECTIONS_MAX_RECORDS:
            raise SalesforceBadRequestError(
                f"collections {what} accepts at most {COLLECTIONS_MAX_RECORDS} "
                f"records per call, got {count}."
            )

    def collections_create(
        self, records: list[dict[str, Any]], all_or_none: bool = False
    ) -> Any:
        """Create up to 200 records (each needs ``attributes.type``)."""
        self._check_collection_size(len(records), "create")
        return self._client.request(
            "POST",
            f"{self._client.data_base}/composite/sobjects",
            json={"allOrNone": all_or_none, "records": records},
        )

    def collections_update(
        self, records: list[dict[str, Any]], all_or_none: bool = False
    ) -> Any:
        """Update up to 200 records (each needs ``attributes.type`` + ``Id``)."""
        self._check_collection_size(len(records), "update")
        return self._client.request(
            "PATCH",
            f"{self._client.data_base}/composite/sobjects",
            json={"allOrNone": all_or_none, "records": records},
        )

    def collections_delete(self, ids: list[str], all_or_none: bool = False) -> Any:
        """Delete up to 200 records by id. Gated by ``allow_destructive``."""
        self._guard_destructive("records.collections_delete")
        self._check_collection_size(len(ids), "delete")
        return self._client.request(
            "DELETE",
            f"{self._client.data_base}/composite/sobjects",
            params={"ids": ",".join(ids), "allOrNone": str(all_or_none).lower()},
        )
