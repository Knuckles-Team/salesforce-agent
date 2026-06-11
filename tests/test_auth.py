"""Auth flow matrix: client-credentials, refresh-token, JWT bearer, static token."""

import httpx
import pytest

from salesforce_agent.auth import (
    JWT_GRANT_TYPE,
    PRODUCTION_LOGIN_URL,
    REDACTED,
    SANDBOX_LOGIN_URL,
    SalesforceAuth,
    SalesforceConfig,
)
from salesforce_agent.salesforce_response_models import SalesforceAuthError
from tests.conftest import FakeSalesforce, make_api, make_config


@pytest.mark.concept("SFDC-1.1")
class TestConfig:
    def test_api_version_normalized(self):
        config = SalesforceConfig(
            access_token="t", instance_url="https://x", api_version="62.0"
        )
        assert config.api_version == "v62.0"

    def test_production_login_url_default(self):
        config = SalesforceConfig(client_id="a", client_secret="b")
        assert config.login_url == PRODUCTION_LOGIN_URL

    def test_sandbox_login_url(self):
        config = SalesforceConfig(client_id="a", client_secret="b", sandbox=True)
        assert config.login_url == SANDBOX_LOGIN_URL

    def test_token_url_prefers_my_domain(self):
        config = SalesforceConfig(
            client_id="a",
            client_secret="b",
            instance_url="https://org.my.salesforce.com/",
        )
        assert config.token_url == "https://org.my.salesforce.com/services/oauth2/token"

    def test_token_url_falls_back_to_login_url(self):
        config = SalesforceConfig(client_id="a", client_secret="b", sandbox=True)
        assert config.token_url == f"{SANDBOX_LOGIN_URL}/services/oauth2/token"

    def test_flow_autodetect_client_credentials(self):
        assert (
            SalesforceConfig(client_id="a", client_secret="b").flow
            == "client_credentials"
        )

    def test_flow_autodetect_refresh_token(self):
        config = SalesforceConfig(client_id="a", refresh_token="r")
        assert config.flow == "refresh_token"

    def test_flow_autodetect_access_token(self):
        assert SalesforceConfig(access_token="t").flow == "access_token"

    def test_flow_autodetect_jwt(self):
        config = SalesforceConfig(
            client_id="a", jwt_subject="user@example.com", jwt_private_key="PEM"
        )
        assert config.flow == "jwt_bearer"

    def test_explicit_flow_wins(self):
        config = SalesforceConfig(
            auth_flow="client_credentials",
            client_id="a",
            client_secret="b",
            refresh_token="r",
        )
        assert config.flow == "client_credentials"

    def test_unknown_flow_rejected(self):
        with pytest.raises(SalesforceAuthError, match="Unknown auth flow"):
            SalesforceConfig(auth_flow="password")

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "https://org.my.salesforce.com")
        monkeypatch.setenv("SALESFORCE_CLIENT_ID", "cid")
        monkeypatch.setenv("SALESFORCE_CLIENT_SECRET", "sec")
        monkeypatch.setenv("SALESFORCE_API_VERSION", "61.0")
        monkeypatch.setenv("SALESFORCE_SANDBOX", "true")
        monkeypatch.setenv("SALESFORCE_ALLOW_DESTRUCTIVE", "true")
        monkeypatch.setenv("SALESFORCE_MAX_QUERY_RECORDS", "77")
        config = SalesforceConfig.from_env()
        assert config.flow == "client_credentials"
        assert config.api_version == "v61.0"
        assert config.sandbox is True
        assert config.allow_destructive is True
        assert config.max_query_records == 77


@pytest.mark.concept("SFDC-1.1")
class TestClientCredentialsFlow:
    def test_token_request_form(self, fake):
        auth = SalesforceAuth(
            make_config(fake), transport=httpx.MockTransport(fake.handler)
        )
        token, instance = auth.token()
        assert token == "TOKEN-1"
        assert instance == fake.instance
        form = fake.token_requests[0]
        assert form["grant_type"] == "client_credentials"
        assert form["client_id"] == "the-consumer-key"
        assert form["client_secret"] == "the-consumer-secret"

    def test_token_cached_between_calls(self, fake):
        auth = SalesforceAuth(
            make_config(fake), transport=httpx.MockTransport(fake.handler)
        )
        auth.token()
        auth.token()
        assert fake.token_counter == 1

    def test_expired_token_refetched(self, fake):
        fake.expires_in = 0  # expires immediately (skew clamps to >= 0)
        auth = SalesforceAuth(
            make_config(fake), transport=httpx.MockTransport(fake.handler)
        )
        auth.token()
        auth.token()
        assert fake.token_counter == 2

    def test_invalidate_forces_refetch(self, fake):
        auth = SalesforceAuth(
            make_config(fake), transport=httpx.MockTransport(fake.handler)
        )
        auth.token()
        auth.invalidate()
        token, _ = auth.token()
        assert token == "TOKEN-2"

    def test_token_endpoint_error_is_typed_and_redacted(self, fake):
        fake.token_error = {
            "error": "invalid_client",
            "error_description": "bad secret the-consumer-secret",
        }
        auth = SalesforceAuth(
            make_config(fake), transport=httpx.MockTransport(fake.handler)
        )
        with pytest.raises(SalesforceAuthError) as excinfo:
            auth.token()
        assert "the-consumer-secret" not in str(excinfo.value)
        assert REDACTED in str(excinfo.value)
        assert excinfo.value.error_code == "invalid_client"

    def test_missing_credentials_raise(self):
        config = SalesforceConfig()
        auth = SalesforceAuth(config)
        with pytest.raises(SalesforceAuthError, match="No Salesforce credentials"):
            auth.token()


@pytest.mark.concept("SFDC-1.1")
class TestRefreshTokenFlow:
    def test_form_fields(self, fake):
        config = make_config(
            fake, auth_flow="refresh_token", refresh_token="the-refresh-token"  # sanitizer:ignore
        )
        auth = SalesforceAuth(config, transport=httpx.MockTransport(fake.handler))
        auth.token()
        form = fake.token_requests[0]
        assert form["grant_type"] == "refresh_token"
        assert form["refresh_token"] == "the-refresh-token"
        assert form["client_id"] == "the-consumer-key"
        assert form["client_secret"] == "the-consumer-secret"

    def test_secret_optional(self, fake):
        config = make_config(
            fake,
            auth_flow="refresh_token",
            refresh_token="the-refresh-token",  # sanitizer:ignore
            client_secret="",
        )
        auth = SalesforceAuth(config, transport=httpx.MockTransport(fake.handler))
        auth.token()
        assert "client_secret" not in fake.token_requests[0]

    def test_instance_url_from_token_response(self, fake):
        config = make_config(
            fake, auth_flow="refresh_token", refresh_token="r", instance_url=""
        )
        config.login_url = fake.instance  # token endpoint must still resolve
        auth = SalesforceAuth(config, transport=httpx.MockTransport(fake.handler))
        _, instance = auth.token()
        assert instance == fake.instance


@pytest.mark.concept("SFDC-1.1")
class TestJwtBearerFlow:
    @pytest.fixture
    def rsa_pem(self) -> str:
        cryptography = pytest.importorskip("cryptography")
        del cryptography
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()

    def test_assertion_grant_posted(self, fake, rsa_pem):
        config = make_config(
            fake,
            auth_flow="jwt_bearer",
            jwt_subject="integration@example.com",
            jwt_private_key=rsa_pem,
        )
        auth = SalesforceAuth(config, transport=httpx.MockTransport(fake.handler))
        token, _ = auth.token()
        assert token == "TOKEN-1"
        form = fake.token_requests[0]
        assert form["grant_type"] == JWT_GRANT_TYPE
        assert form["assertion"].count(".") == 2

    @staticmethod
    def _decode_segment(segment: str) -> dict:
        import base64
        import json

        return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))

    def test_assertion_claims(self, fake, rsa_pem):
        config = make_config(
            fake,
            auth_flow="jwt_bearer",
            jwt_subject="integration@example.com",
            jwt_private_key=rsa_pem,
        )
        auth = SalesforceAuth(config, transport=httpx.MockTransport(fake.handler))
        assertion = auth._jwt_assertion()
        header_b64, claims_b64, _ = assertion.split(".")
        header = self._decode_segment(header_b64)
        claims = self._decode_segment(claims_b64)
        assert header == {"alg": "RS256"}
        assert claims["iss"] == "the-consumer-key"
        assert claims["sub"] == "integration@example.com"
        assert claims["aud"] == PRODUCTION_LOGIN_URL  # default audience = login URL
        assert claims["exp"] > 0

    def test_private_key_from_file(self, fake, rsa_pem, tmp_path):
        key_path = tmp_path / "server.key"
        key_path.write_text(rsa_pem)
        config = make_config(
            fake,
            auth_flow="jwt_bearer",
            jwt_subject="integration@example.com",
            jwt_private_key_path=str(key_path),
        )
        auth = SalesforceAuth(config, transport=httpx.MockTransport(fake.handler))
        token, _ = auth.token()
        assert token == "TOKEN-1"

    def test_explicit_audience(self, fake, rsa_pem):
        config = make_config(
            fake,
            auth_flow="jwt_bearer",
            jwt_subject="integration@example.com",
            jwt_private_key=rsa_pem,
            jwt_audience="https://test.salesforce.com",
        )
        auth = SalesforceAuth(config, transport=httpx.MockTransport(fake.handler))
        _, claims_b64, _ = auth._jwt_assertion().split(".")
        assert self._decode_segment(claims_b64)["aud"] == "https://test.salesforce.com"


@pytest.mark.concept("SFDC-1.1")
class TestStaticAccessToken:
    def test_returns_configured_pair(self, fake):
        config = make_config(fake, auth_flow="access_token", access_token="STATIC")
        auth = SalesforceAuth(config, transport=httpx.MockTransport(fake.handler))
        assert auth.token() == ("STATIC", fake.instance)
        assert fake.token_counter == 0
        assert auth.can_refresh is False

    def test_requires_instance_url(self):
        config = SalesforceConfig(access_token="STATIC")
        auth = SalesforceAuth(config)
        with pytest.raises(SalesforceAuthError, match="SALESFORCE_INSTANCE_URL"):
            auth.token()


@pytest.mark.concept("SFDC-1.1")
class TestRefreshOn401:
    def test_api_call_retries_once_with_fresh_token(self, fake, api):
        fake.seed_query([{"Id": "1"}], page_size=10)
        api.describe.limits()  # establishes TOKEN-1
        fake.expire_current_token()
        result = api.describe.limits()
        assert "DailyApiRequests" in result
        assert fake.token_counter == 2

    def test_second_401_raises_auth_error(self, fake, api):
        api.describe.limits()
        fake.reject_api_tokens = True  # even re-issued tokens stay rejected
        with pytest.raises(SalesforceAuthError):
            api.describe.limits()
        assert fake.token_counter == 2  # exactly one retry, then surfaced

    def test_static_token_does_not_retry(self, fake):
        client = make_api(fake, auth_flow="access_token", access_token="STATIC")
        with pytest.raises(SalesforceAuthError):
            client.describe.limits()
        assert fake.token_counter == 0
        client.close()


@pytest.mark.concept("SFDC-1.3")
class TestRedaction:
    def test_redact_strips_all_secrets(self, fake):
        config = make_config(fake, refresh_token="refresh-secret")
        auth = SalesforceAuth(config, transport=httpx.MockTransport(fake.handler))
        auth.token()
        text = auth.redact(
            "token TOKEN-1 secret the-consumer-secret refresh refresh-secret"
        )
        assert "TOKEN-1" not in text
        assert "the-consumer-secret" not in text
        assert "refresh-secret" not in text
        assert text.count(REDACTED) == 3

    def test_api_error_bodies_are_redacted(self, fake, api):
        api.describe.limits()
        fake.force_error = (
            400,
            '[{"message": "echoing bearer TOKEN-1", "errorCode": "BAD"}]',
        )
        with pytest.raises(Exception) as excinfo:
            api.describe.limits()
        assert "TOKEN-1" not in str(excinfo.value)


def test_fake_salesforce_is_importable():
    assert FakeSalesforce().instance.startswith("https://")
