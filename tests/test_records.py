"""Record CRUD, composite batching, collections, and destructive gating."""

import json

import pytest

from salesforce_agent.salesforce_response_models import (
    DestructiveOperationBlockedError,
    SalesforceBadRequestError,
)


@pytest.mark.concept("SFDC-1.2")
class TestCrud:
    def test_get(self, fake, api):
        record = api.records.get("Account", "001A")
        assert record["Id"] == "001A"

    def test_get_with_field_selection(self, fake, api):
        record = api.records.get("Account", "001A", fields=["Name", "Industry"])
        assert record["_requested_fields"] == "Name,Industry"

    def test_create(self, fake, api):
        result = api.records.create("Account", {"Name": "Acme"})
        assert result == {"id": "001NEW", "success": True, "errors": []}
        sent = json.loads(fake.api_requests[-1].content)
        assert sent == {"Name": "Acme"}

    def test_update_returns_success_envelope(self, fake, api):
        result = api.records.update("Account", "001A", {"Name": "Acme 2"})
        assert result["success"] is True
        assert result["status_code"] == 204
        assert fake.api_requests[-1].method == "PATCH"

    def test_upsert_by_external_id(self, fake, api):
        result = api.records.upsert(
            "Account", "External_Id__c", "X-9", {"Name": "Acme"}
        )
        assert result["created"] is True
        assert fake.api_requests[-1].url.path.endswith(
            "/sobjects/Account/External_Id__c/X-9"
        )


@pytest.mark.concept("SFDC-1.3")
class TestDeleteGating:
    def test_delete_blocked_by_default(self, fake, api):
        with pytest.raises(DestructiveOperationBlockedError):
            api.records.delete("Account", "001A")
        assert fake.api_requests == []  # never reached the wire

    def test_delete_allowed_when_enabled(self, fake, api_destructive):
        result = api_destructive.records.delete("Account", "001A")
        assert result["success"] is True
        assert fake.api_requests[-1].method == "DELETE"

    def test_collections_delete_blocked_by_default(self, fake, api):
        with pytest.raises(DestructiveOperationBlockedError):
            api.records.collections_delete(["001A", "001B"])

    def test_composite_delete_subrequest_blocked(self, fake, api):
        with pytest.raises(DestructiveOperationBlockedError):
            api.records.composite(
                [
                    {
                        "method": "delete",
                        "url": "/services/data/v62.0/sobjects/Account/001A",
                        "referenceId": "del1",
                    }
                ]
            )


@pytest.mark.concept("SFDC-1.2")
class TestComposite:
    def _subrequest(self, i: int) -> dict:
        return {
            "method": "POST",
            "url": "/services/data/v62.0/sobjects/Account",
            "referenceId": f"ref{i}",
            "body": {"Name": f"Acme {i}"},
        }

    def test_composite_batches_subrequests(self, fake, api):
        result = api.records.composite(
            [self._subrequest(i) for i in range(3)], all_or_none=True
        )
        assert len(result["compositeResponse"]) == 3
        sent = json.loads(fake.api_requests[-1].content)
        assert sent["allOrNone"] is True
        assert [s["referenceId"] for s in sent["compositeRequest"]] == [
            "ref0",
            "ref1",
            "ref2",
        ]

    def test_composite_caps_at_25(self, fake, api):
        with pytest.raises(SalesforceBadRequestError, match="at most 25"):
            api.records.composite([self._subrequest(i) for i in range(26)])

    def test_composite_accepts_exactly_25(self, fake, api):
        result = api.records.composite([self._subrequest(i) for i in range(25)])
        assert len(result["compositeResponse"]) == 25

    def test_composite_rejects_empty(self, fake, api):
        with pytest.raises(SalesforceBadRequestError, match="at least one"):
            api.records.composite([])


@pytest.mark.concept("SFDC-1.2")
class TestCollections:
    @staticmethod
    def _record(i: int) -> dict:
        return {"attributes": {"type": "Account"}, "Name": f"Acme {i}"}

    def test_collections_create(self, fake, api):
        result = api.records.collections_create(
            [self._record(i) for i in range(3)], all_or_none=True
        )
        assert [r["success"] for r in result] == [True, True, True]
        sent = json.loads(fake.api_requests[-1].content)
        assert sent["allOrNone"] is True
        assert len(sent["records"]) == 3

    def test_collections_update(self, fake, api):
        result = api.records.collections_update([self._record(0)])
        assert result[0]["success"] is True
        assert fake.api_requests[-1].method == "PATCH"

    def test_collections_caps_at_200(self, fake, api):
        with pytest.raises(SalesforceBadRequestError, match="at most 200"):
            api.records.collections_create([self._record(i) for i in range(201)])

    def test_collections_accepts_exactly_200(self, fake, api):
        result = api.records.collections_create([self._record(i) for i in range(200)])
        assert len(result) == 200

    def test_collections_rejects_empty(self, fake, api):
        with pytest.raises(SalesforceBadRequestError, match="no records"):
            api.records.collections_update([])

    def test_collections_delete_when_enabled(self, fake, api_destructive):
        result = api_destructive.records.collections_delete(
            ["001A", "001B"], all_or_none=True
        )
        assert [r["id"] for r in result] == ["001A", "001B"]
        request = fake.api_requests[-1]
        assert request.url.params["ids"] == "001A,001B"
        assert request.url.params["allOrNone"] == "true"

    def test_collections_delete_caps_at_200(self, fake, api_destructive):
        with pytest.raises(SalesforceBadRequestError, match="at most 200"):
            api_destructive.records.collections_delete(
                [f"001{i:03d}" for i in range(201)]
            )
