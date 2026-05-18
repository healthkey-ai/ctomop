"""MyChart OAuth flow orchestration.

Two entry points:
- `create_authorization_url` builds the Epic authorize URL with PKCE + state.
- `finish_authorization` exchanges the code for tokens, persists them, and
  triggers the FHIR_EXTRACT Airflow DAG so the patient's clinical data starts
  flowing into OMOP.
"""
import base64
import datetime
import hashlib
import logging
import secrets
import urllib.parse

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from omop_core.models import EpicEndpoint, EpicOrganization, FhirToken, OAuth2State
from patient_portal.infrastructure.airflow_client import (
    AirflowClient,
    AirflowDag,
    AirflowError,
)
from patient_portal.mychart.client import EpicClient
from patient_portal.mychart.dtos import (
    CreateAuthUrlRequest,
    CreateAuthUrlResponse,
    FinishAuthRequest,
    FinishAuthResponse,
    SmartConfiguration,
    TokenExchangeRequest,
)

_logger = logging.getLogger(__name__)

_SMART_CONFIG_CACHE_TIMEOUT = 60 * 60  # 1 hour
_SMART_CONFIG_CACHE_KEY = "mychart:smart_configuration:{endpoint_id}"


class MyChartFlowError(Exception):
    """Raised when the OAuth flow can't proceed (bad state, unknown org, etc.)."""


class MyChartService:
    def __init__(
        self,
        epic_client: EpicClient,
        airflow_client: AirflowClient | None,
        client_id: str,
        redirect_uri: str,
        scopes: str,
        target_organization_slug: str,
    ):
        """All config injected — settings.py reading happens at the view layer."""
        self._epic_client = epic_client
        self._airflow_client = airflow_client
        self._client_id = client_id
        self._redirect_uri = redirect_uri
        self._scopes = scopes
        self._target_organization_slug = target_organization_slug

    # ---- /start ----------------------------------------------------------

    def create_authorization_url(self, request: CreateAuthUrlRequest) -> CreateAuthUrlResponse:
        try:
            epic_org = EpicOrganization.objects.select_related("endpoint").get(
                alias=request.organization_alias,
                is_active=True,
            )
        except EpicOrganization.DoesNotExist:
            raise MyChartFlowError(f"Unknown EpicOrganization alias: {request.organization_alias}")

        endpoint = epic_org.endpoint
        smart_config = self._get_smart_configuration(endpoint)

        code_verifier = _b64url(secrets.token_bytes(32))
        code_challenge = _b64url(hashlib.sha256(code_verifier.encode("utf-8")).digest())
        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(16)

        OAuth2State.objects.create(
            state=state,
            code_verifier=code_verifier,
            provider=OAuth2State.PROVIDER_EPIC,
            user_id=request.user_id,
            endpoint=endpoint,
            metadata={
                "token_endpoint": smart_config.token_endpoint,
                "nonce": nonce,
                "epic_organization_alias": epic_org.alias,
            },
        )

        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": self._scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "aud": endpoint.url,
        }
        url = smart_config.authorization_endpoint + "?" + urllib.parse.urlencode(params)
        return CreateAuthUrlResponse(authorization_url=url, state=state)

    # ---- /finish ---------------------------------------------------------

    def finish_authorization(self, request: FinishAuthRequest) -> FinishAuthResponse:
        try:
            db_state = OAuth2State.objects.select_related("endpoint").get(
                state=request.state,
                provider=OAuth2State.PROVIDER_EPIC,
            )
        except OAuth2State.DoesNotExist:
            raise MyChartFlowError("Unknown or expired state")

        if db_state.user_id != request.user_id:
            raise MyChartFlowError("State does not belong to the requesting user")

        token_endpoint = db_state.metadata.get("token_endpoint")
        if not token_endpoint:
            raise MyChartFlowError("State is missing token_endpoint metadata")

        token_response = self._epic_client.exchange_code_for_tokens(
            TokenExchangeRequest(
                token_endpoint=token_endpoint,
                code=request.code,
                redirect_uri=self._redirect_uri,
                client_id=self._client_id,
                code_verifier=db_state.code_verifier,
            )
        )

        expires_at = timezone.now() + datetime.timedelta(seconds=token_response.expires_in)
        fhir_patient_id = token_response.patient or ""
        endpoint = db_state.endpoint
        endpoint_url = endpoint.url

        with transaction.atomic():
            fhir_token, _ = FhirToken.objects.update_or_create(
                user_id=request.user_id,
                endpoint=endpoint,
                defaults={
                    "access_token": token_response.access_token,
                    "refresh_token": token_response.refresh_token,
                    "id_token": token_response.id_token,
                    "expires_at": expires_at,
                    "scope": token_response.scope,
                    "fhir_patient_id": fhir_patient_id,
                },
            )
            db_state.delete()

        dag_run_id = self._trigger_extract_dag(fhir_token, fhir_patient_id)

        return FinishAuthResponse(
            fhir_patient_id=fhir_patient_id,
            endpoint_url=endpoint_url,
            dag_run_id=dag_run_id,
        )

    # ---- helpers ---------------------------------------------------------

    def _get_smart_configuration(self, endpoint: EpicEndpoint) -> SmartConfiguration:
        cache_key = _SMART_CONFIG_CACHE_KEY.format(endpoint_id=endpoint.id)
        cached = cache.get(cache_key)
        if cached:
            return SmartConfiguration(**cached)
        config = self._epic_client.get_smart_configuration(endpoint.url)
        cache.set(cache_key, config.__dict__, timeout=_SMART_CONFIG_CACHE_TIMEOUT)
        return config

    def _trigger_extract_dag(self, fhir_token: FhirToken, fhir_patient_id: str) -> str | None:
        if self._airflow_client is None:
            _logger.warning("Airflow client not configured; skipping FHIR_EXTRACT trigger")
            return None
        if not fhir_patient_id:
            _logger.warning(
                "FhirToken %s has no fhir_patient_id; skipping FHIR_EXTRACT trigger",
                fhir_token.id,
            )
            return None
        conf = {
            "fhir_token_id": fhir_token.id,
            "endpoint_url": fhir_token.endpoint.url,
            "fhir_patient_id": fhir_patient_id,
            "target_organization_slug": self._target_organization_slug,
        }
        try:
            return self._airflow_client.create_dag_run(
                dag=AirflowDag.FHIR_EXTRACT,
                dag_run_prefix=f"mychart-user{fhir_token.user_id}",
                conf=conf,
            )
        except AirflowError as e:
            _logger.error("Failed to trigger FHIR_EXTRACT for token %s: %s", fhir_token.id, e)
            return None


def _b64url(data: bytes) -> str:
    """RFC 7636 base64url with stripped padding."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")
