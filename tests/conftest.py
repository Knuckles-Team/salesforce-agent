"""Shared fixtures: an in-memory fake Salesforce org behind httpx.MockTransport."""

import json
import re
from urllib.parse import parse_qs

import httpx
import pytest

from salesforce_agent.api_client import Api
from salesforce_agent.auth import SalesforceConfig

API_V = "v62.0"
DATA_BASE = f"/services/data/{API_V}"


class FakeSalesforce:
    """Stateful fake org: token endpoint + the REST surfaces this repo wraps."""

    instance = "https://example.my.salesforce.com"

    def __init__(self):
        self.token_requests: list[dict] = []
        self.api_requests: list[httpx.Request] = []
        self.token_counter = 0
        self.active_token: str | None = None
        self.expires_in: int | None = None
        self.token_error: dict | None = None
        self.reject_api_tokens = False
        self.force_error: tuple[int, str] | None = None  # one-shot (status, body)
        self.query_records: list[dict] = []
        self.query_page_size = 2
        self.bulk_jobs: dict[str, dict] = {}
        self.bulk_uploads: dict[str, bytes] = {}
        self.bulk_results_csv = '"sf__Id","sf__Created","Name"\n"001A","true","Acme"\n'
        self.bulk_results_locator: str | None = None

    # ------------------------------------------------------------------ #
    def expire_current_token(self) -> None:
        """Make the org reject the currently issued token (forces re-auth)."""
        self.active_token = None

    def seed_query(self, records: list[dict], page_size: int = 2) -> None:
        self.query_records = records
        self.query_page_size = page_size

    def _query_page(self, page: int) -> dict:
        size = self.query_page_size
        chunk = self.query_records[page * size : (page + 1) * size]
        done = (page + 1) * size >= len(self.query_records)
        body = {
            "totalSize": len(self.query_records),
            "done": done,
            "records": chunk,
        }
        if not done:
            body["nextRecordsUrl"] = f"{DATA_BASE}/query/01g-{page + 1}"
        return body

    # ------------------------------------------------------------------ #
    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path == "/services/oauth2/token":
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            self.token_requests.append(form)
            if self.token_error is not None:
                return httpx.Response(400, json=self.token_error)
            self.token_counter += 1
            self.active_token = f"TOKEN-{self.token_counter}"
            payload = {
                "access_token": self.active_token,
                "instance_url": self.instance,
                "token_type": "Bearer",
                "issued_at": "1717000000000",
            }
            if self.expires_in is not None:
                payload["expires_in"] = self.expires_in
            return httpx.Response(200, json=payload)

        self.api_requests.append(request)

        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if self.reject_api_tokens or not token or token != self.active_token:
            return httpx.Response(
                401,
                json=[
                    {
                        "message": "Session expired or invalid",
                        "errorCode": "INVALID_SESSION_ID",
                    }
                ],
            )

        if self.force_error is not None:
            status, body = self.force_error
            self.force_error = None
            return httpx.Response(
                status, text=body, headers={"Content-Type": "application/json"}
            )

        return self._route(request, path)

    # ------------------------------------------------------------------ #
    def _route(self, request: httpx.Request, path: str) -> httpx.Response:
        params = dict(request.url.params)
        method = request.method

        # --- OAuth identity / analytics ---------------------------------
        if path == "/services/oauth2/userinfo":
            return httpx.Response(
                200,
                json={
                    "user_id": "005xx0000000001",
                    "organization_id": "00Dxx0000000001",
                    "preferred_username": "integration@example.com",
                },
            )
        if path == f"{DATA_BASE}/analytics/reports":
            return httpx.Response(
                200, json=[{"id": "00Oxx0000000001", "name": "Pipeline"}]
            )
        match = re.fullmatch(f"{DATA_BASE}/analytics/reports/(.+)", path)
        if match:
            return httpx.Response(
                200,
                json={
                    "attributes": {"reportId": match.group(1)},
                    "allData": True,
                    "factMap": {"T!T": {"aggregates": [{"value": 42}]}},
                    "includeDetails": params.get("includeDetails"),
                },
            )

        # --- Query / search ----------------------------------------------
        if path in (f"{DATA_BASE}/query", f"{DATA_BASE}/queryAll") and "q" in params:
            return httpx.Response(200, json=self._query_page(0))
        if path == f"{DATA_BASE}/query/" and "explain" in params:
            return httpx.Response(
                200,
                json={"plans": [{"cardinality": 1, "leadingOperationType": "Index"}]},
            )
        match = re.fullmatch(f"{DATA_BASE}/query(?:All)?/01g-(\\d+)", path)
        if match:
            return httpx.Response(200, json=self._query_page(int(match.group(1))))
        if path == f"{DATA_BASE}/search/":
            return httpx.Response(
                200,
                json={
                    "searchRecords": [
                        {"attributes": {"type": "Account"}, "Id": "001A"}
                    ],
                    "sosl": params.get("q"),
                },
            )

        # --- Limits / describe ---------------------------------------------
        if path == f"{DATA_BASE}/limits":
            return httpx.Response(
                200,
                json={"DailyApiRequests": {"Max": 15000, "Remaining": 14998}},
            )
        if path == f"{DATA_BASE}/limits/recordCount":
            wanted = params.get("sObjects", "Account").split(",")
            return httpx.Response(
                200,
                json={"sObjects": [{"name": n, "count": 10} for n in wanted]},
            )
        if path == f"{DATA_BASE}/sobjects":
            return httpx.Response(
                200,
                json={
                    "encoding": "UTF-8",
                    "sobjects": [{"name": "Account"}, {"name": "Contact"}],
                },
            )
        match = re.fullmatch(f"{DATA_BASE}/sobjects/(\\w+)/describe", path)
        if match:
            return httpx.Response(
                200,
                json={
                    "name": match.group(1),
                    "fields": [
                        {
                            "name": "Industry",
                            "type": "picklist",
                            "picklistValues": [{"value": "Energy"}],
                        }
                    ],
                    "childRelationships": [{"childSObject": "Contact"}],
                },
            )

        # --- Composite / collections ---------------------------------------
        if path == f"{DATA_BASE}/composite" and method == "POST":
            body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "compositeResponse": [
                        {
                            "referenceId": sub.get("referenceId"),
                            "httpStatusCode": 200,
                            "body": {"id": "001A"},
                        }
                        for sub in body["compositeRequest"]
                    ]
                },
            )
        if path == f"{DATA_BASE}/composite/sobjects":
            if method in ("POST", "PATCH"):
                body = json.loads(request.content)
                return httpx.Response(
                    200,
                    json=[
                        {"id": f"001{i:03d}", "success": True, "errors": []}
                        for i, _ in enumerate(body["records"])
                    ],
                )
            if method == "DELETE":
                ids = params.get("ids", "").split(",")
                return httpx.Response(
                    200,
                    json=[{"id": i, "success": True, "errors": []} for i in ids],
                )

        # --- Bulk API 2.0 ----------------------------------------------------
        if path == f"{DATA_BASE}/jobs/ingest" and method == "POST":
            body = json.loads(request.content)
            job_id = f"750-{len(self.bulk_jobs) + 1}"
            job = {"id": job_id, "state": "Open", **body}
            self.bulk_jobs[job_id] = job
            return httpx.Response(200, json=job)
        if path == f"{DATA_BASE}/jobs/ingest" and method == "GET":
            return httpx.Response(
                200, json={"done": True, "records": list(self.bulk_jobs.values())}
            )
        match = re.fullmatch(f"{DATA_BASE}/jobs/ingest/([^/]+)/batches", path)
        if match and method == "PUT":
            self.bulk_uploads[match.group(1)] = request.content
            return httpx.Response(201)
        match = re.fullmatch(
            f"{DATA_BASE}/jobs/ingest/([^/]+)/"
            "(successfulResults|failedResults|unprocessedrecords)",
            path,
        )
        if match and method == "GET":
            headers = {
                "Content-Type": "text/csv",
                "Sforce-NumberOfRecords": "1",
            }
            if self.bulk_results_locator:
                headers["Sforce-Locator"] = self.bulk_results_locator
            return httpx.Response(200, text=self.bulk_results_csv, headers=headers)
        match = re.fullmatch(f"{DATA_BASE}/jobs/ingest/([^/]+)", path)
        if match:
            job_id = match.group(1)
            job = self.bulk_jobs.get(job_id)
            if job is None:
                return httpx.Response(
                    404,
                    json=[{"message": "job not found", "errorCode": "NOT_FOUND"}],
                )
            if method == "PATCH":
                job["state"] = json.loads(request.content)["state"]
                if job["state"] == "UploadComplete":
                    job["state"] = "JobComplete"  # fast-forward processing
                return httpx.Response(200, json=job)
            if method == "DELETE":
                del self.bulk_jobs[job_id]
                return httpx.Response(204)
            return httpx.Response(200, json=job)

        # --- sObject record CRUD ---------------------------------------------
        match = re.fullmatch(f"{DATA_BASE}/sobjects/(\\w+)", path)
        if match and method == "POST":
            return httpx.Response(
                201, json={"id": "001NEW", "success": True, "errors": []}
            )
        match = re.fullmatch(f"{DATA_BASE}/sobjects/(\\w+)/([\\w-]+)", path)
        if match:
            if method == "GET":
                record = {
                    "attributes": {"type": match.group(1)},
                    "Id": match.group(2),
                    "Name": "Acme",
                }
                fields = params.get("fields")
                if fields:
                    record["_requested_fields"] = fields
                return httpx.Response(200, json=record)
            if method in ("PATCH", "DELETE"):
                return httpx.Response(204)
        match = re.fullmatch(f"{DATA_BASE}/sobjects/(\\w+)/(\\w+)/([\\w.@-]+)", path)
        if match and method == "PATCH":  # upsert by external id
            return httpx.Response(
                201, json={"id": "001UPS", "success": True, "created": True}
            )

        return httpx.Response(
            404,
            json=[
                {"message": f"no route for {method} {path}", "errorCode": "NOT_FOUND"}
            ],
        )


def make_config(fake: FakeSalesforce, **overrides) -> SalesforceConfig:
    defaults = dict(
        instance_url=fake.instance,
        client_id="the-consumer-key",
        client_secret="the-consumer-secret",
        api_version=API_V,
    )
    defaults.update(overrides)
    return SalesforceConfig(**defaults)


def make_api(fake: FakeSalesforce, **overrides) -> Api:
    return Api(
        config=make_config(fake, **overrides),
        transport=httpx.MockTransport(fake.handler),
    )


@pytest.fixture
def fake() -> FakeSalesforce:
    return FakeSalesforce()


@pytest.fixture
def api(fake):
    client = make_api(fake)
    yield client
    client.close()


@pytest.fixture
def api_destructive(fake):
    client = make_api(fake, allow_destructive=True)
    yield client
    client.close()
