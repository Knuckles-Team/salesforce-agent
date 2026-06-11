"""CONCEPT:SFDC-1.0 Shared httpx base client for the Salesforce REST API.

Owned thin client (no ``simple-salesforce``): a single httpx.Client that
attaches the cached bearer token, maps failures to typed errors
(:mod:`salesforce_agent.models`), retries exactly once on 401 after
invalidating the token cache, and redacts secrets from anything it raises.

REST API reference:
https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_rest.htm
"""

from typing import Any

import httpx

from salesforce_agent.auth import SalesforceAuth
from salesforce_agent.models import map_response_error


class ApiClientBase:
    """Token-aware request runner shared by every resource client."""

    def __init__(
        self,
        auth: SalesforceAuth,
        transport: httpx.BaseTransport | None = None,
    ):
        self.auth = auth
        self._http = httpx.Client(
            timeout=auth.config.timeout,
            verify=auth.config.verify,
            transport=transport,
            follow_redirects=True,
        )

    @property
    def data_base(self) -> str:
        """Versioned REST root, e.g. ``/services/data/v62.0``."""
        return f"/services/data/{self.auth.config.api_version}"

    def request_raw(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        content: str | bytes | None = None,
        headers: dict[str, str] | None = None,
        _retried: bool = False,
    ) -> httpx.Response:
        """Run one authenticated request and return the raw response.

        ``endpoint`` is joined onto the org's instance URL unless it is
        already absolute. A 401 invalidates the token cache and retries once
        (refresh-on-401); any remaining HTTP >= 400 raises a typed
        :class:`~salesforce_agent.models.SalesforceError` with secrets
        redacted from the message.
        """
        token, instance_url = self.auth.token()
        url = endpoint if endpoint.startswith("http") else f"{instance_url}{endpoint}"
        request_headers = {"Authorization": f"Bearer {token}"}
        if headers:
            request_headers.update(headers)

        response = self._http.request(
            method=method,
            url=url,
            params=params,
            json=json,
            content=content,
            headers=request_headers,
        )

        if response.status_code == 401 and not _retried and self.auth.can_refresh:
            self.auth.invalidate()
            return self.request_raw(
                method,
                endpoint,
                params=params,
                json=json,
                content=content,
                headers=headers,
                _retried=True,
            )

        if response.status_code >= 400:
            raise map_response_error(
                response.status_code, response.text, redact=self.auth.redact
            )
        return response

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        content: str | bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Run a request and return parsed JSON (or a success/text envelope)."""
        response = self.request_raw(
            method,
            endpoint,
            params=params,
            json=json,
            content=content,
            headers=headers,
        )
        if response.status_code == 204 or not response.text.strip():
            return {"success": True, "status_code": response.status_code}
        if "json" in response.headers.get("content-type", ""):
            return response.json()
        return {"status_code": response.status_code, "text": response.text}

    def close(self) -> None:
        self._http.close()
