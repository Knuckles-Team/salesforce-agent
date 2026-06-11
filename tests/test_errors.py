"""Salesforce error-envelope mapping to the typed exception hierarchy."""

import pytest

from salesforce_agent.models import (
    SalesforceAuthError,
    SalesforceBadRequestError,
    SalesforceConflictError,
    SalesforceError,
    SalesforceForbiddenError,
    SalesforceNotFoundError,
    SalesforceRateLimitError,
    SalesforceServerError,
    map_response_error,
    parse_error_payload,
)


@pytest.mark.concept("SFDC-1.0")
class TestParseErrorPayload:
    def test_rest_array_envelope(self):
        message, code, fields, details = parse_error_payload(
            '[{"message": "No such column X", "errorCode": "INVALID_FIELD",'
            ' "fields": ["X"]}]'
        )
        assert message == "No such column X"
        assert code == "INVALID_FIELD"
        assert fields == ["X"]
        assert details[0]["errorCode"] == "INVALID_FIELD"

    def test_multiple_errors_joined(self):
        message, code, _, details = parse_error_payload(
            '[{"message": "first", "errorCode": "A"},'
            ' {"message": "second", "errorCode": "B"}]'
        )
        assert message == "first; second"
        assert code == "A"
        assert len(details) == 2

    def test_oauth_object_envelope(self):
        message, code, _, _ = parse_error_payload(
            '{"error": "invalid_grant", "error_description": "expired token"}'
        )
        assert message == "expired token"
        assert code == "invalid_grant"

    def test_non_json_body(self):
        message, code, fields, details = parse_error_payload("<html>boom</html>")
        assert message == "<html>boom</html>"
        assert code is None
        assert fields == []
        assert details == []

    def test_empty_body(self):
        message, _, _, _ = parse_error_payload("")
        assert message == "Unknown Salesforce error"


@pytest.mark.concept("SFDC-1.0")
class TestMapResponseError:
    BODY = '[{"message": "boom", "errorCode": "GENERIC"}]'

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (400, SalesforceBadRequestError),
            (401, SalesforceAuthError),
            (403, SalesforceForbiddenError),
            (404, SalesforceNotFoundError),
            (409, SalesforceConflictError),
            (412, SalesforceConflictError),
            (428, SalesforceConflictError),
            (418, SalesforceError),
            (500, SalesforceServerError),
            (503, SalesforceServerError),
        ],
    )
    def test_status_mapping(self, status, expected):
        error = map_response_error(status, self.BODY)
        assert type(error) is expected
        assert error.status_code == status
        assert error.error_code == "GENERIC"

    def test_rate_limit_special_case(self):
        error = map_response_error(
            403,
            '[{"message": "limit", "errorCode": "REQUEST_LIMIT_EXCEEDED"}]',
        )
        assert isinstance(error, SalesforceRateLimitError)
        assert isinstance(error, SalesforceForbiddenError)  # still catchable as 403

    def test_redaction_hook_applied(self):
        error = map_response_error(
            400,
            '[{"message": "leaked SECRET", "errorCode": "X"}]',
            redact=lambda text: text.replace("SECRET", "***"),
        )
        assert "SECRET" not in str(error)


@pytest.mark.concept("SFDC-1.0")
class TestWireErrors:
    def test_malformed_query_maps_to_bad_request(self, fake, api):
        api.describe.limits()  # warm the token
        fake.force_error = (
            400,
            '[{"message": "unexpected token", "errorCode": "MALFORMED_QUERY"}]',
        )
        with pytest.raises(SalesforceBadRequestError) as excinfo:
            api.soql.query("SELECT FROM")
        assert excinfo.value.error_code == "MALFORMED_QUERY"

    def test_rate_limit_maps_from_wire(self, fake, api):
        api.describe.limits()
        fake.force_error = (
            403,
            '[{"message": "TotalRequests Limit exceeded.",'
            ' "errorCode": "REQUEST_LIMIT_EXCEEDED"}]',
        )
        with pytest.raises(SalesforceRateLimitError):
            api.describe.limits()

    def test_server_error_maps_from_wire(self, fake, api):
        api.describe.limits()
        fake.force_error = (500, '[{"message": "boom", "errorCode": "UNKNOWN"}]')
        with pytest.raises(SalesforceServerError):
            api.describe.limits()

    def test_unknown_route_is_not_found(self, fake, api):
        from salesforce_agent.models import SalesforceNotFoundError

        api.describe.limits()
        with pytest.raises(SalesforceNotFoundError):
            api._base.request("GET", "/services/data/v62.0/nonexistent")
