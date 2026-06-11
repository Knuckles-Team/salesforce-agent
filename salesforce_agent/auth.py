"""CONCEPT:SFDC-1.1 Salesforce OAuth2 flows, token cache, and client factory.

Implements three server-to-server OAuth2 flows against the Salesforce token
endpoint (``/services/oauth2/token``), plus a static access-token mode:

- **client_credentials** — Connected App consumer key/secret. Salesforce
  requires the *My Domain* token endpoint for this flow, so set
  ``SALESFORCE_INSTANCE_URL`` (or ``SALESFORCE_LOGIN_URL``) to the org's My
  Domain URL.
  https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_client_credentials_flow.htm
- **refresh_token** — long-lived refresh token from a prior web-server/agent
  flow.
  https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_refresh_token_flow.htm
- **jwt_bearer** — RS256-signed JWT assertion (``cryptography`` optional
  extra: ``pip install salesforce-agent[jwt]``).
  https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_jwt_flow.htm

Tokens are cached in-process with expiry tracking (``expires_in`` when the
endpoint returns it, else a configurable TTL) and refreshed transparently;
the HTTP layer additionally invalidates the cache and retries once on 401.
Sandbox orgs authenticate against ``https://test.salesforce.com``; production
against ``https://login.salesforce.com``.
"""

import base64
import json
import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx
from agent_utilities.base_utilities import get_logger, to_boolean

if TYPE_CHECKING:
    from salesforce_agent.api_client import Api

from salesforce_agent.salesforce_response_models import (
    SalesforceAuthError,
    parse_error_payload,
)

logger = get_logger(__name__)

DEFAULT_API_VERSION = "v62.0"
PRODUCTION_LOGIN_URL = "https://login.salesforce.com"
SANDBOX_LOGIN_URL = "https://test.salesforce.com"
JWT_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
REDACTED = "***REDACTED***"

AUTH_FLOWS = ("client_credentials", "refresh_token", "jwt_bearer", "access_token")


@dataclass
class SalesforceConfig:
    """Connection + safety configuration for one Salesforce org."""

    instance_url: str = ""
    login_url: str = ""
    sandbox: bool = False
    api_version: str = DEFAULT_API_VERSION
    auth_flow: str = ""
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    access_token: str = ""
    jwt_subject: str = ""
    jwt_private_key: str = ""
    jwt_private_key_path: str = ""
    jwt_audience: str = ""
    timeout: float = 30.0
    verify: bool = True
    token_ttl_seconds: int = 1800
    allow_destructive: bool = False
    max_query_records: int = 2000
    bulk_results_max_bytes: int = 5_000_000
    report_max_rows: int = 2000
    _resolved_flow: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        self.instance_url = self.instance_url.rstrip("/")
        if not self.login_url:
            self.login_url = SANDBOX_LOGIN_URL if self.sandbox else PRODUCTION_LOGIN_URL
        self.login_url = self.login_url.rstrip("/")
        version = self.api_version or DEFAULT_API_VERSION
        if not version.startswith("v"):
            version = f"v{version}"
        self.api_version = version
        self._resolved_flow = self._resolve_flow()

    def _resolve_flow(self) -> str:
        if self.auth_flow:
            if self.auth_flow not in AUTH_FLOWS:
                raise SalesforceAuthError(
                    f"Unknown auth flow {self.auth_flow!r}; expected one of {AUTH_FLOWS}."
                )
            return self.auth_flow
        if self.access_token:
            return "access_token"
        if self.refresh_token:
            return "refresh_token"
        if (self.jwt_private_key or self.jwt_private_key_path) and self.jwt_subject:
            return "jwt_bearer"
        if self.client_id and self.client_secret:
            return "client_credentials"
        return ""

    @property
    def flow(self) -> str:
        return self._resolved_flow

    @property
    def token_url(self) -> str:
        """Token endpoint — prefers My Domain (required for client_credentials)."""
        base = self.instance_url or self.login_url
        return f"{base}/services/oauth2/token"

    @classmethod
    def from_env(cls) -> "SalesforceConfig":
        """Build configuration from ``SALESFORCE_*`` environment variables."""
        return cls(
            instance_url=os.getenv("SALESFORCE_INSTANCE_URL", ""),
            login_url=os.getenv("SALESFORCE_LOGIN_URL", ""),
            sandbox=to_boolean(os.getenv("SALESFORCE_SANDBOX", "False")),
            api_version=os.getenv("SALESFORCE_API_VERSION", DEFAULT_API_VERSION),
            auth_flow=os.getenv("SALESFORCE_AUTH_FLOW", ""),
            client_id=os.getenv("SALESFORCE_CLIENT_ID", ""),
            client_secret=os.getenv("SALESFORCE_CLIENT_SECRET", ""),
            refresh_token=os.getenv("SALESFORCE_REFRESH_TOKEN", ""),
            access_token=os.getenv("SALESFORCE_ACCESS_TOKEN", ""),
            jwt_subject=os.getenv("SALESFORCE_JWT_SUBJECT", ""),
            jwt_private_key=os.getenv("SALESFORCE_JWT_PRIVATE_KEY", ""),
            jwt_private_key_path=os.getenv("SALESFORCE_JWT_PRIVATE_KEY_PATH", ""),
            jwt_audience=os.getenv("SALESFORCE_JWT_AUDIENCE", ""),
            timeout=float(os.getenv("SALESFORCE_TIMEOUT", "30")),
            verify=to_boolean(os.getenv("SALESFORCE_SSL_VERIFY", "True")),
            token_ttl_seconds=int(os.getenv("SALESFORCE_TOKEN_TTL_SECONDS", "1800")),
            allow_destructive=to_boolean(
                os.getenv("SALESFORCE_ALLOW_DESTRUCTIVE", "False")
            ),
            max_query_records=int(os.getenv("SALESFORCE_MAX_QUERY_RECORDS", "2000")),
            bulk_results_max_bytes=int(
                os.getenv("SALESFORCE_BULK_RESULTS_MAX_BYTES", "5000000")
            ),
            report_max_rows=int(os.getenv("SALESFORCE_REPORT_MAX_ROWS", "2000")),
        )


def _b64url(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


class SalesforceAuth:
    """Token cache + OAuth2 flow driver for one configured org."""

    TOKEN_EXPIRY_SKEW_SECONDS = 60

    def __init__(
        self,
        config: SalesforceConfig,
        transport: httpx.BaseTransport | None = None,
    ):
        self.config = config
        self._http = httpx.Client(
            timeout=config.timeout, verify=config.verify, transport=transport
        )
        self._access_token: str | None = None
        self._instance_url: str = config.instance_url
        self._expires_at: float = 0.0

    # ------------------------------------------------------------------ #
    # Public surface
    # ------------------------------------------------------------------ #
    @property
    def can_refresh(self) -> bool:
        """Static access-token mode has nothing to fall back to on 401."""
        return self.config.flow != "access_token"

    def token(self) -> tuple[str, str]:
        """Return a valid ``(access_token, instance_url)`` pair, fetching if needed."""
        flow = self.config.flow
        if not flow:
            raise SalesforceAuthError(
                "No Salesforce credentials configured: set SALESFORCE_ACCESS_TOKEN, "
                "SALESFORCE_REFRESH_TOKEN, SALESFORCE_CLIENT_ID/SECRET, or JWT settings."
            )
        if flow == "access_token":
            if not self.config.instance_url:
                raise SalesforceAuthError(
                    "SALESFORCE_INSTANCE_URL is required with a static access token."
                )
            return self.config.access_token, self.config.instance_url
        if self._access_token and time.monotonic() < self._expires_at:
            return self._access_token, self._instance_url
        self._fetch_token()
        assert self._access_token is not None
        return self._access_token, self._instance_url

    def invalidate(self) -> None:
        """Drop the cached token so the next call re-authenticates."""
        self._access_token = None
        self._expires_at = 0.0

    def redact(self, text: str) -> str:
        """Strip every known secret out of ``text`` before it is logged/raised."""
        secrets = [
            self._access_token,
            self.config.access_token,
            self.config.refresh_token,
            self.config.client_secret,
        ]
        for secret in secrets:
            if secret:
                text = text.replace(secret, REDACTED)
        return text

    def close(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------ #
    # Flow internals
    # ------------------------------------------------------------------ #
    def _fetch_token(self) -> None:
        flow = self.config.flow
        if flow == "client_credentials":
            data = {
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
            }
        elif flow == "refresh_token":
            data = {
                "grant_type": "refresh_token",
                "client_id": self.config.client_id,
                "refresh_token": self.config.refresh_token,
            }
            if self.config.client_secret:
                data["client_secret"] = self.config.client_secret
        elif flow == "jwt_bearer":
            data = {"grant_type": JWT_GRANT_TYPE, "assertion": self._jwt_assertion()}
        else:  # pragma: no cover - guarded by token()
            raise SalesforceAuthError(f"Auth flow {flow!r} cannot fetch tokens.")

        response = self._http.post(self.config.token_url, data=data)
        if response.status_code >= 400:
            message, error_code, _, _ = parse_error_payload(response.text)
            raise SalesforceAuthError(
                f"Salesforce token request failed ({flow}): {self.redact(message)}",
                status_code=response.status_code,
                error_code=error_code,
            )
        payload = response.json()
        self._access_token = payload["access_token"]
        self._instance_url = str(
            payload.get("instance_url") or self.config.instance_url
        ).rstrip("/")
        if not self._instance_url:
            raise SalesforceAuthError(
                "Token response carried no instance_url and none was configured."
            )
        expires_in = payload.get("expires_in")
        ttl = (
            int(expires_in) if expires_in is not None else self.config.token_ttl_seconds
        )
        self._expires_at = (
            time.monotonic() + ttl - min(self.TOKEN_EXPIRY_SKEW_SECONDS, ttl // 2)
        )
        logger.info(
            "Salesforce token acquired",
            extra={"flow": flow, "instance_url": self._instance_url},
        )

    def _private_key_pem(self) -> bytes:
        if self.config.jwt_private_key:
            return self.config.jwt_private_key.encode()
        with open(self.config.jwt_private_key_path, "rb") as handle:
            return handle.read()

    def _jwt_assertion(self) -> str:
        """Build the RS256-signed JWT assertion for the JWT bearer flow.

        Claims per
        https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_jwt_flow.htm:
        ``iss`` = consumer key, ``sub`` = username, ``aud`` = login URL,
        ``exp`` = now + 3 minutes.
        """
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding, rsa
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise SalesforceAuthError(
                "The JWT bearer flow needs the 'cryptography' package: "
                "pip install salesforce-agent[jwt]"
            ) from exc

        header = {"alg": "RS256"}
        claims = {
            "iss": self.config.client_id,
            "sub": self.config.jwt_subject,
            "aud": self.config.jwt_audience or self.config.login_url,
            "exp": int(time.time()) + 180,
        }
        signing_input = (
            _b64url(json.dumps(header, separators=(",", ":")).encode())
            + b"."
            + _b64url(json.dumps(claims, separators=(",", ":")).encode())
        )
        key = serialization.load_pem_private_key(self._private_key_pem(), password=None)
        if not isinstance(key, rsa.RSAPrivateKey):
            raise SalesforceAuthError(
                "JWT bearer flow requires an RSA private key (RS256)."
            )
        signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        return (signing_input + b"." + _b64url(signature)).decode()


def get_client() -> "Api":
    """Build a configured Salesforce :class:`Api` facade from the environment."""
    from salesforce_agent.api_client import Api

    return Api(config=SalesforceConfig.from_env())
