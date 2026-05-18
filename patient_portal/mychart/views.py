"""DRF view layer for the MyChart OAuth flow."""
import logging

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from omop_core.models import EpicOrganization
from patient_portal.infrastructure.airflow_client import AirflowClientImplementation
from patient_portal.mychart.client import EpicClientImplementation
from patient_portal.mychart.dtos import CreateAuthUrlRequest, FinishAuthRequest
from patient_portal.mychart.serializers import (
    EpicOrganizationSerializer,
    FinishRequestSerializer,
    StartRequestSerializer,
)
from patient_portal.mychart.service import MyChartFlowError, MyChartService

_logger = logging.getLogger(__name__)


def _build_service() -> MyChartService:
    """Construct a MyChartService with config from settings.

    Wrapped so tests can monkeypatch the EpicClient / AirflowClient if needed.
    """
    epic_client = EpicClientImplementation(client_id=settings.EPIC_CLIENT_ID)
    if settings.AIRFLOW_URL:
        airflow_client = AirflowClientImplementation(
            airflow_url=settings.AIRFLOW_URL,
            airflow_username=settings.AIRFLOW_USERNAME,
            airflow_password=settings.AIRFLOW_PASSWORD,
        )
    else:
        airflow_client = None
    return MyChartService(
        epic_client=epic_client,
        airflow_client=airflow_client,
        client_id=settings.EPIC_CLIENT_ID,
        redirect_uri=settings.EPIC_REDIRECT_URI,
        scopes=settings.EPIC_SCOPES,
        target_organization_slug=settings.MYCHART_TARGET_ORGANIZATION_SLUG,
    )


class MyChartViewSet(viewsets.ViewSet):
    """OAuth-client endpoints for SMART-on-FHIR (Epic / MyChart)."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def organizations(self, request):
        """List EpicOrganizations the patient can pick from."""
        qs = EpicOrganization.objects.filter(is_active=True).order_by("title")
        return Response(EpicOrganizationSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"])
    def start(self, request):
        """Build the Epic authorization URL. Body: {organization_alias}."""
        if not settings.EPIC_CLIENT_ID:
            return Response(
                {"error": "EPIC_CLIENT_ID is not configured on this server"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = StartRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _build_service()
        try:
            result = service.create_authorization_url(
                CreateAuthUrlRequest(
                    user_id=request.user.id,
                    organization_alias=serializer.validated_data["organization_alias"],
                )
            )
        except MyChartFlowError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"url": result.authorization_url, "state": result.state})

    @action(detail=False, methods=["post"])
    def finish(self, request):
        """Exchange the code for tokens. Body: {code, state}."""
        serializer = FinishRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _build_service()
        try:
            result = service.finish_authorization(
                FinishAuthRequest(
                    user_id=request.user.id,
                    code=serializer.validated_data["code"],
                    state=serializer.validated_data["state"],
                )
            )
        except MyChartFlowError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "fhir_patient_id": result.fhir_patient_id,
                "endpoint_url": result.endpoint_url,
                "dag_run_id": result.dag_run_id,
            }
        )
