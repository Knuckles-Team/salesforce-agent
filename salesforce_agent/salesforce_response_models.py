"""CONCEPT:SFDC-1.0 Typed Salesforce error envelope mapping.

Salesforce REST resources report failures as a JSON *array* of error objects
(``[{"message": ..., "errorCode": ..., "fields": [...]}]``), while the OAuth2
token endpoint reports ``{"error": ..., "error_description": ...}``. This
module normalizes both shapes into a typed exception hierarchy so callers can
catch by failure class instead of string-matching response bodies.

Error envelope reference:
https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/errorcodes.htm
"""

import json
from collections.abc import Callable
from typing import Any


class SalesforceError(Exception):
    """Base error for every Salesforce API failure."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        fields: list[str] | None = None,
        details: list[dict[str, Any]] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.fields = fields or []
        self.details = details or []


class SalesforceAuthError(SalesforceError):
    """401 / OAuth token endpoint failures (INVALID_SESSION_ID, invalid_grant)."""


class SalesforceBadRequestError(SalesforceError):
    """400 — malformed SOQL/SOSL, bad field names, invalid request bodies."""


class SalesforceForbiddenError(SalesforceError):
    """403 — missing object/field permissions or refused request."""


class SalesforceRateLimitError(SalesforceForbiddenError):
    """403 REQUEST_LIMIT_EXCEEDED — daily API request allocation exhausted."""


class SalesforceNotFoundError(SalesforceError):
    """404 — unknown sObject, record id, or REST resource."""


class SalesforceConflictError(SalesforceError):
    """409 / 412 / 428 — edit conflicts and precondition failures."""


class SalesforceServerError(SalesforceError):
    """5xx — Salesforce-side failure."""


class DestructiveOperationBlockedError(SalesforceError):
    """A delete/hardDelete was requested while ``allow_destructive`` is False."""

    def __init__(self, operation: str):
        super().__init__(
            f"Destructive operation {operation!r} blocked: set "
            "SALESFORCE_ALLOW_DESTRUCTIVE=true (or allow_destructive=True) "
            "to permit deletes.",
            error_code="DESTRUCTIVE_OPERATION_BLOCKED",
        )
        self.operation = operation


def parse_error_payload(
    text: str,
) -> tuple[str, str | None, list[str], list[dict[str, Any]]]:
    """Extract (message, error_code, fields, details) from an error body.

    Handles the REST array envelope, the OAuth object envelope, and opaque
    non-JSON bodies.
    """
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return text.strip() or "Unknown Salesforce error", None, [], []

    if isinstance(payload, list) and payload:
        details = [e for e in payload if isinstance(e, dict)]
        first = details[0] if details else {}
        message = "; ".join(
            str(e.get("message", "")) for e in details if e.get("message")
        )
        return (
            message or "Unknown Salesforce error",
            first.get("errorCode"),
            list(first.get("fields") or []),
            details,
        )
    if isinstance(payload, dict):
        if "error" in payload:  # OAuth token endpoint envelope
            message = str(
                payload.get("error_description") or payload.get("error") or ""
            )
            return message, str(payload.get("error")), [], [payload]
        message = str(payload.get("message") or payload.get("msg") or text)
        return message, payload.get("errorCode"), [], [payload]
    return text.strip() or "Unknown Salesforce error", None, [], []


_STATUS_MAP: dict[int, type[SalesforceError]] = {
    400: SalesforceBadRequestError,
    401: SalesforceAuthError,
    403: SalesforceForbiddenError,
    404: SalesforceNotFoundError,
    409: SalesforceConflictError,
    412: SalesforceConflictError,
    428: SalesforceConflictError,
}


def map_response_error(
    status_code: int,
    text: str,
    redact: Callable[[str], str] | None = None,
) -> SalesforceError:
    """Map an HTTP failure to a typed :class:`SalesforceError` subclass."""
    message, error_code, fields, details = parse_error_payload(text)
    if redact is not None:
        message = redact(message)

    cls: type[SalesforceError]
    if status_code == 403 and error_code == "REQUEST_LIMIT_EXCEEDED":
        cls = SalesforceRateLimitError
    elif status_code >= 500:
        cls = SalesforceServerError
    else:
        cls = _STATUS_MAP.get(status_code, SalesforceError)

    return cls(
        f"Salesforce API error {status_code}: {message}",
        status_code=status_code,
        error_code=error_code,
        fields=fields,
        details=details,
    )
