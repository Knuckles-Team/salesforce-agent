"""Bulk API 2.0 job lifecycle, destructive gating, and result size caps."""

import json

import pytest

from salesforce_agent.models import (
    DestructiveOperationBlockedError,
    SalesforceBadRequestError,
    SalesforceNotFoundError,
)

CSV = "Name\nAcme\nGlobex\n"


@pytest.mark.concept("SFDC-1.4")
class TestJobLifecycle:
    def test_full_ingest_lifecycle(self, fake, api):
        job = api.bulk.create_ingest_job("Account", "insert")
        assert job["state"] == "Open"
        assert job["object"] == "Account"
        assert job["contentType"] == "CSV"

        upload = api.bulk.upload(job["id"], CSV)
        assert upload["success"] is True
        assert fake.bulk_uploads[job["id"]] == CSV.encode()
        upload_request = next(
            r for r in fake.api_requests if r.url.path.endswith("/batches")
        )
        assert upload_request.headers["Content-Type"] == "text/csv"

        closed = api.bulk.close(job["id"])
        assert closed["state"] == "JobComplete"  # fake fast-forwards processing

        status = api.bulk.status(job["id"])
        assert status["state"] == "JobComplete"

        results = api.bulk.results(job["id"], kind="successful")
        assert "Acme" in results["content"]
        assert results["truncated"] is False

    def test_create_upsert_job_requires_external_id(self, fake, api):
        with pytest.raises(SalesforceBadRequestError, match="external_id_field"):
            api.bulk.create_ingest_job("Account", "upsert")

    def test_create_upsert_job_sends_external_id(self, fake, api):
        api.bulk.create_ingest_job(
            "Account", "upsert", external_id_field="External_Id__c"
        )
        sent = json.loads(fake.api_requests[-1].content)
        assert sent["externalIdFieldName"] == "External_Id__c"
        assert sent["operation"] == "upsert"

    def test_unknown_operation_rejected(self, fake, api):
        with pytest.raises(SalesforceBadRequestError, match="Unknown bulk operation"):
            api.bulk.create_ingest_job("Account", "merge")

    def test_abort(self, fake, api):
        job = api.bulk.create_ingest_job("Account", "insert")
        aborted = api.bulk.abort(job["id"])
        assert aborted["state"] == "Aborted"

    def test_list_jobs(self, fake, api):
        api.bulk.create_ingest_job("Account", "insert")
        api.bulk.create_ingest_job("Contact", "update")
        listing = api.bulk.list_jobs()
        assert len(listing["records"]) == 2

    def test_delete_job_metadata(self, fake, api):
        job = api.bulk.create_ingest_job("Account", "insert")
        api.bulk.delete_job(job["id"])
        with pytest.raises(SalesforceNotFoundError):
            api.bulk.status(job["id"])

    def test_status_unknown_job_raises_not_found(self, fake, api):
        with pytest.raises(SalesforceNotFoundError):
            api.bulk.status("750-missing")


@pytest.mark.concept("SFDC-1.3")
class TestBulkDestructiveGating:
    def test_delete_job_blocked_by_default(self, fake, api):
        with pytest.raises(DestructiveOperationBlockedError):
            api.bulk.create_ingest_job("Account", "delete")
        assert fake.api_requests == []

    def test_hard_delete_blocked_by_default(self, fake, api):
        with pytest.raises(DestructiveOperationBlockedError):
            api.bulk.create_ingest_job("Account", "hardDelete")

    def test_delete_job_allowed_when_enabled(self, fake, api_destructive):
        job = api_destructive.bulk.create_ingest_job("Account", "delete")
        assert job["operation"] == "delete"


@pytest.mark.concept("SFDC-1.3")
class TestBulkResultCaps:
    def test_results_capped_and_flagged(self, fake, api):
        job = api.bulk.create_ingest_job("Account", "insert")
        fake.bulk_results_csv = "Name\n" + "A" * 10_000
        results = api.bulk.results(job["id"], kind="failed", max_bytes=100)
        assert results["truncated"] is True
        assert results["bytes"] == 100
        assert len(results["content"]) == 100

    def test_results_cap_default_from_config(self, fake):
        from tests.conftest import make_api

        client = make_api(fake, bulk_results_max_bytes=50)
        job = client.bulk.create_ingest_job("Account", "insert")
        fake.bulk_results_csv = "Name\n" + "B" * 1_000
        results = client.bulk.results(job["id"])
        assert results["truncated"] is True
        assert results["bytes"] == 50
        client.close()

    def test_results_locator_paging(self, fake, api):
        job = api.bulk.create_ingest_job("Account", "insert")
        fake.bulk_results_locator = "LOCATOR-2"
        results = api.bulk.results(job["id"], kind="successful")
        assert results["locator"] == "LOCATOR-2"
        page2 = api.bulk.results(job["id"], kind="successful", locator="LOCATOR-2")
        assert page2["number_of_records"] == "1"
        assert fake.api_requests[-1].url.params["locator"] == "LOCATOR-2"

    def test_unknown_result_kind_rejected(self, fake, api):
        with pytest.raises(SalesforceBadRequestError, match="Unknown result kind"):
            api.bulk.results("750-1", kind="bogus")

    def test_unprocessed_results_endpoint(self, fake, api):
        job = api.bulk.create_ingest_job("Account", "insert")
        api.bulk.results(job["id"], kind="unprocessed")
        assert fake.api_requests[-1].url.path.endswith("/unprocessedrecords")
