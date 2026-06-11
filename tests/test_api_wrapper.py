"""CONCEPT:SFDC-1.1 API client request/response behavior (mocked transport)."""

import pytest

from salesforce_agent.salesforce_response_models import SalesforceError
from tests.conftest import make_api


@pytest.mark.concept("SFDC-1.1")
class TestApiWrapper:
    def test_request_sends_bearer_token(self, fake):
        api = make_api(fake)
        try:
            api.describe.limits()
            assert fake.api_requests, "no API request was issued"
            auth = fake.api_requests[-1].headers.get("Authorization", "")
            assert auth.startswith("Bearer ")
        finally:
            api.close()

    def test_api_error_maps_to_typed_exception(self, fake):
        api = make_api(fake)
        try:
            fake.force_error = (400, '[{"message": "bad", "errorCode": "X"}]')
            with pytest.raises(SalesforceError):
                api.describe.limits()
        finally:
            api.close()

    def test_facade_composes_domain_clients(self, fake):
        api = make_api(fake)
        try:
            for domain in ("soql", "records", "describe", "bulk", "admin"):
                assert hasattr(api, domain), f"Api facade is missing {domain!r}"
        finally:
            api.close()
