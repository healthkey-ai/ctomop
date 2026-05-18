"""HTTP client for Epic's SMART-on-FHIR endpoints.

Abstract base + a `requests`-backed implementation so tests can swap in a fake.
"""
import abc
import logging
import urllib.parse

import requests

from patient_portal.mychart.dtos import (
    SmartConfiguration,
    TokenExchangeRequest,
    TokenExchangeResponse,
)

_logger = logging.getLogger(__name__)


class EpicClient(abc.ABC):
    @abc.abstractmethod
    def get_smart_configuration(self, base_url: str) -> SmartConfiguration:
        """Fetch `.well-known/smart-configuration` from the FHIR base URL."""

    @abc.abstractmethod
    def exchange_code_for_tokens(self, request: TokenExchangeRequest) -> TokenExchangeResponse:
        """Exchange the authorization code for tokens (public PKCE client)."""


class EpicClientImplementation(EpicClient):
    def __init__(self, client_id: str, timeout_seconds: int = 30):
        self._client_id = client_id
        self._timeout = timeout_seconds

    def get_smart_configuration(self, base_url: str) -> SmartConfiguration:
        url = urllib.parse.urljoin(base_url.rstrip("/") + "/", ".well-known/smart-configuration")
        headers = {
            "Accept": "application/json",
            "Epic-Client-ID": self._client_id,
        }
        response = requests.get(url, headers=headers, timeout=self._timeout)
        response.raise_for_status()
        data = response.json()
        return SmartConfiguration(
            authorization_endpoint=data["authorization_endpoint"],
            token_endpoint=data["token_endpoint"],
            issuer=data.get("issuer"),
            jwks_uri=data.get("jwks_uri"),
        )

    def exchange_code_for_tokens(self, request: TokenExchangeRequest) -> TokenExchangeResponse:
        body = {
            "grant_type": "authorization_code",
            "code": request.code,
            "redirect_uri": request.redirect_uri,
            "client_id": request.client_id,
            "code_verifier": request.code_verifier,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        response = requests.post(
            request.token_endpoint,
            data=body,
            headers=headers,
            timeout=self._timeout,
        )
        if response.status_code != 200:
            _logger.warning(
                "Epic token exchange failed: status=%s body=%s",
                response.status_code, response.text[:500],
            )
            response.raise_for_status()
        data = response.json()
        return TokenExchangeResponse(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            id_token=data.get("id_token", ""),
            expires_in=int(data.get("expires_in", 3600)),
            scope=data.get("scope", ""),
            patient=data.get("patient"),
        )
