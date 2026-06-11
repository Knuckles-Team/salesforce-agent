"""CONCEPT:SFDC-1.4 Bulk API 2.0 ingest job client (CSV in, CSV results out).

Resources (Bulk API 2.0 developer guide):
- Create job:   https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/create_job.htm
- Upload data:  https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/upload_job_data.htm
- Close/abort:  https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/close_job.htm
- Job info:     https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/get_job_info.htm
- Results:      https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/get_job_successful_results.htm

CONCEPT:SFDC-1.3 — ``delete``/``hardDelete`` ingest jobs are gated by
``allow_destructive``; result downloads are size-capped
(``SALESFORCE_BULK_RESULTS_MAX_BYTES``).
"""

from typing import Any

from salesforce_agent.api.api_client_base import ApiClientBase
from salesforce_agent.models import (
    DestructiveOperationBlockedError,
    SalesforceBadRequestError,
)

INGEST_OPERATIONS = {"insert", "update", "upsert", "delete", "hardDelete"}
DESTRUCTIVE_OPERATIONS = {"delete", "hardDelete"}
RESULT_KINDS = {
    "successful": "successfulResults",
    "failed": "failedResults",
    "unprocessed": "unprocessedrecords",
}


class BulkClient:
    """Bulk API 2.0 ingest job lifecycle: create → upload → close → results."""

    def __init__(self, base: ApiClientBase):
        self._client = base

    @property
    def _jobs_base(self) -> str:
        return f"{self._client.data_base}/jobs/ingest"

    def create_ingest_job(
        self,
        sobject: str,
        operation: str,
        external_id_field: str | None = None,
        line_ending: str = "LF",
        column_delimiter: str = "COMMA",
    ) -> dict[str, Any]:
        """Create an ingest job (insert/update/upsert/delete/hardDelete).

        ``upsert`` requires ``external_id_field``. Delete operations are
        gated by ``allow_destructive``.
        """
        if operation not in INGEST_OPERATIONS:
            raise SalesforceBadRequestError(
                f"Unknown bulk operation {operation!r}; "
                f"expected one of {sorted(INGEST_OPERATIONS)}."
            )
        if operation in DESTRUCTIVE_OPERATIONS:
            if not self._client.auth.config.allow_destructive:
                raise DestructiveOperationBlockedError(f"bulk.{operation}")
        if operation == "upsert" and not external_id_field:
            raise SalesforceBadRequestError("Bulk upsert requires external_id_field.")
        body: dict[str, Any] = {
            "object": sobject,
            "operation": operation,
            "contentType": "CSV",
            "lineEnding": line_ending,
            "columnDelimiter": column_delimiter,
        }
        if external_id_field:
            body["externalIdFieldName"] = external_id_field
        return self._client.request("POST", self._jobs_base, json=body)

    def upload(self, job_id: str, csv_data: str | bytes) -> dict[str, Any]:
        """Upload the job's CSV payload (``PUT .../batches``, text/csv)."""
        return self._client.request(
            "PUT",
            f"{self._jobs_base}/{job_id}/batches",
            content=csv_data,
            headers={"Content-Type": "text/csv", "Accept": "application/json"},
        )

    def close(self, job_id: str) -> dict[str, Any]:
        """Mark upload complete so Salesforce starts processing the job."""
        return self._client.request(
            "PATCH", f"{self._jobs_base}/{job_id}", json={"state": "UploadComplete"}
        )

    def abort(self, job_id: str) -> dict[str, Any]:
        """Abort a job that has not finished processing."""
        return self._client.request(
            "PATCH", f"{self._jobs_base}/{job_id}", json={"state": "Aborted"}
        )

    def status(self, job_id: str) -> dict[str, Any]:
        """Job info: state, counts of processed/failed records, timing."""
        return self._client.request("GET", f"{self._jobs_base}/{job_id}")

    def list_jobs(self) -> dict[str, Any]:
        """List ingest jobs (most recent first, paged by Salesforce)."""
        return self._client.request("GET", self._jobs_base)

    def delete_job(self, job_id: str) -> dict[str, Any]:
        """Delete the job *metadata* (not org data) once it is terminal."""
        return self._client.request("DELETE", f"{self._jobs_base}/{job_id}")

    def results(
        self,
        job_id: str,
        kind: str = "successful",
        locator: str | None = None,
        max_bytes: int | None = None,
    ) -> dict[str, Any]:
        """Download job results CSV (successful / failed / unprocessed).

        The body is capped at ``max_bytes`` (default
        ``SALESFORCE_BULK_RESULTS_MAX_BYTES``); a truncated download is
        flagged and carries the ``Sforce-Locator`` header so the caller can
        page through the remainder.
        """
        if kind not in RESULT_KINDS:
            raise SalesforceBadRequestError(
                f"Unknown result kind {kind!r}; expected one of {sorted(RESULT_KINDS)}."
            )
        cap = max_bytes or self._client.auth.config.bulk_results_max_bytes
        params = {"locator": locator} if locator else None
        response = self._client.request_raw(
            "GET",
            f"{self._jobs_base}/{job_id}/{RESULT_KINDS[kind]}",
            params=params,
            headers={"Accept": "text/csv"},
        )
        body = response.content
        truncated = len(body) > cap
        return {
            "job_id": job_id,
            "kind": kind,
            "content": body[:cap].decode("utf-8", errors="replace"),
            "bytes": min(len(body), cap),
            "truncated": truncated,
            "locator": response.headers.get("Sforce-Locator"),
            "number_of_records": response.headers.get("Sforce-NumberOfRecords"),
        }
