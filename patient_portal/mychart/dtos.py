"""Dataclass DTOs at every MyChart-flow boundary.

API view → Service → Infrastructure client communicate only via these types.
Keeps Django request/response objects out of the service layer.
"""
from dataclasses import dataclass


@dataclass
class CreateAuthUrlRequest:
    user_id: int
    organization_alias: str


@dataclass
class CreateAuthUrlResponse:
    authorization_url: str
    state: str


@dataclass
class FinishAuthRequest:
    user_id: int
    code: str
    state: str


@dataclass
class FinishAuthResponse:
    fhir_patient_id: str
    endpoint_url: str
    dag_run_id: str | None  # None if Airflow not configured


@dataclass
class SmartConfiguration:
    authorization_endpoint: str
    token_endpoint: str
    issuer: str | None = None
    jwks_uri: str | None = None


@dataclass
class TokenExchangeRequest:
    token_endpoint: str
    code: str
    redirect_uri: str
    client_id: str
    code_verifier: str


@dataclass
class TokenExchangeResponse:
    access_token: str
    refresh_token: str
    id_token: str
    expires_in: int
    scope: str
    patient: str | None  # Epic Patient resource id, present for patient launches
