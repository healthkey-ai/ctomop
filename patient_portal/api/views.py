from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from django.contrib.auth.models import User
from django.contrib.auth import logout, login, authenticate
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from omop_core.models import (
    Person, PatientInfo, Concept, ProvenanceRecord,
    ConditionOccurrence, DrugExposure, Measurement, Observation, ProcedureOccurrence,
    PatientDocument, PatientTrialEnrollment,
    # Controlled vocabulary lookup models
    Ethnicity, StemCellTransplant, HistologicType, EstrogenReceptorStatus,
    ProgesteroneReceptorStatus, Her2Status, HrStatus, HrdStatus,
    MutationOrigin, MutationGene, MutationInterpretation, MutationCode,
    TumorStage, NodesStage, DistantMetastasisStage, StagingModality,
    ToxicityGrade, Language, LanguageSkillLevel, BinetStage, ProteinExpression,
    RichterTransformation, TumorBurden, MorphologicVariant, DiseaseActivity,
    PreExistingConditionCategory,
    Disease, CancerStage, KarnofskyScore, EcogStatus, PeripheralNeuropathyGrade,
    InfectionStatus, DiseaseProgression, MeasurableDisease, GelfCriteria,
    FlipIScore, FollicularLymphomaGrade,
    BreastCancerFirstLineTherapy, BreastCancerSecondLineTherapy, BreastCancerLaterLineTherapy,
)
from omop_oncology.models import Episode, EpisodeEvent
from omop_core.services.patient_info_service import refresh_patient_info
from omop_core.services.omop_write_service import sync_to_omop
from omop_core.services.mappings import get_gender_concept
from datetime import datetime
import csv
import json
import logging
from io import StringIO
from .permissions import ScopedTokenPermission, get_request_org
from patient_portal.infrastructure.airflow_client import (
    AirflowClientImplementation,
    AirflowDag,
    AirflowError,
)
from .serializers import (
    UserSerializer, PatientInfoSerializer, PatientListSerializer, ProvenanceRecordSerializer,
    ConditionOccurrenceSerializer, DrugExposureSerializer, MeasurementSerializer,
    ObservationSerializer, ProcedureOccurrenceSerializer,
    EpisodeSerializer, EpisodeEventSerializer,
    PatientDocumentSerializer, PatientTrialEnrollmentSerializer,
)
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SMART on FHIR discovery endpoint
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def smart_configuration(request):
    """
    HL7 SMART on FHIR well-known configuration endpoint.
    Advertises authorization / token endpoints and supported scopes.
    """
    base = request.build_absolute_uri('/').rstrip('/')
    oidc_issuer = getattr(settings, 'OAUTH2_PROVIDER', {}).get('OIDC_ISS_ENDPOINT', '') or base
    return Response({
        'issuer': oidc_issuer,
        'authorization_endpoint': f'{base}/o/authorize/',
        'token_endpoint': f'{base}/o/token/',
        'token_endpoint_auth_methods_supported': ['client_secret_basic', 'client_secret_post', 'none'],
        'revocation_endpoint': f'{base}/o/revoke_token/',
        'introspection_endpoint': f'{base}/o/introspect/',
        'scopes_supported': list(settings.OAUTH2_PROVIDER.get('SCOPES', {}).keys()),
        'response_types_supported': ['code'],
        'grant_types_supported': ['authorization_code', 'client_credentials', 'refresh_token'],
        'code_challenge_methods_supported': ['S256'],
        'capabilities': [
            'launch-standalone',
            'client-public',
            'sso-openid-connect',
            'context-standalone-patient',
            'permission-patient',
            'permission-user',
            'authorize-post',
        ],
    })


@method_decorator(csrf_exempt, name='dispatch')
class CurrentUserViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Just return the logged-in user info - they don't need to be a patient"""
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user_serializer = UserSerializer(request.user)
        return Response({
            'user': user_serializer.data
        })

def _extract_provenance(request):
    """Return (source, source_user_id, modification_reason) from headers or POST body."""
    source = (
        request.data.get('source')
        or request.META.get('HTTP_X_PROVENANCE_SOURCE')
    )
    source_user_id = (
        request.data.get('source_user_id')
        or request.META.get('HTTP_X_PROVENANCE_USER_ID', '')
    )
    modification_reason = request.data.get('modification_reason')
    return source, source_user_id, modification_reason


def _record_provenance(record, source, source_user_id, target_patient_id=None, modification_reason=None, organization=None):
    """Create a ProvenanceRecord pointing at any model instance."""
    ProvenanceRecord.objects.create(
        source=source,
        source_user_id=source_user_id or '',
        target_patient_id=target_patient_id,
        modification_reason=modification_reason,
        organization=organization,
        content_type=ContentType.objects.get_for_model(record),
        object_id=record.pk,
    )


@method_decorator(csrf_exempt, name='dispatch')
class PatientInfoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PatientInfoSerializer
    permission_classes = [ScopedTokenPermission]
    
    def get_queryset(self):
        qs = PatientInfo.objects.all().select_related('person')
        org = get_request_org(self.request)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return PatientListSerializer
        return PatientInfoSerializer
    
    def list(self, request):
        """List all patients - accessible to authenticated users"""
        queryset = self.get_queryset().order_by('-created_at')
        serializer = PatientListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        """Create a new patient record, creating a Person if needed"""
        data = request.data

        # Resolve or create Person
        person_id = data.get('person_id') or data.get('person')
        if person_id:
            try:
                person = Person.objects.get(person_id=int(person_id))
            except Person.DoesNotExist:
                person = Person.objects.create(
                    person_id=int(person_id),
                    year_of_birth=datetime.now().year - 50,
                    gender_source_value='unknown',
                    race_source_value='unknown',
                    ethnicity_source_value='unknown',
                )
        else:
            last_person = Person.objects.order_by('-person_id').first()
            new_person_id = last_person.person_id + 1 if last_person else 1000
            person = Person.objects.create(
                person_id=new_person_id,
                year_of_birth=datetime.now().year - 50,
                gender_source_value='unknown',
                race_source_value='unknown',
                ethnicity_source_value='unknown',
            )

        serializer = PatientInfoSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(person=person)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """Get detailed patient info for a specific person"""
        try:
            person = Person.objects.get(person_id=pk)
            patient_info = PatientInfo.objects.get(person=person)
        except Person.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        except PatientInfo.DoesNotExist:
            return Response({'error': 'Patient information not found'}, status=status.HTTP_404_NOT_FOUND)

        # AUTH-04: enforce per-patient row-level org scoping
        org = get_request_org(request)
        if org is not None and patient_info.organization != org:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get the User associated with this person (not the logged-in user)
        try:
            patient_user = User.objects.get(id=person.person_id)
            user_serializer = UserSerializer(patient_user)
            user_data = user_serializer.data
        except User.DoesNotExist:
            user_data = None

        patient_serializer = PatientInfoSerializer(patient_info)

        return Response({
            'patient_info': patient_serializer.data,
            'user': user_data
        })

    def partial_update(self, request, pk=None):
        """PATCH /api/patient-info/{person_id}/ — update PatientInfo and write through to OMOP."""
        try:
            person = Person.objects.get(person_id=pk)
            patient_info = PatientInfo.objects.get(person=person)
        except Person.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        except PatientInfo.DoesNotExist:
            return Response({'error': 'Patient information not found'}, status=status.HTTP_404_NOT_FOUND)

        org = get_request_org(request)
        if org is not None and patient_info.organization != org:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

        prov_source, prov_user_id, prov_reason = _extract_provenance(request)
        if prov_source == 'ADMIN_CORRECTION' and not prov_reason:
            return Response(
                {'error': 'modification_reason is required when source is ADMIN_CORRECTION'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Capture previous values for fields being changed (exclude provenance meta-fields)
        _prov_meta = {'source', 'source_user_id', 'modification_reason'}
        previous_values = {
            field: getattr(patient_info, field, None)
            for field in request.data
            if field not in _prov_meta and hasattr(patient_info, field)
        }

        serializer = PatientInfoSerializer(patient_info, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if prov_source:
            _record_provenance(patient_info, prov_source, prov_user_id, modification_reason=prov_reason, organization=get_request_org(request))

        changed_fields = {f for f in request.data if f not in _prov_meta}
        try:
            sync_to_omop(patient_info, changed_fields, changed_data=dict(request.data))
        except Exception:
            pass

        return Response({**serializer.data, 'previous_values': previous_values})

    @action(detail=True, methods=['get'], permission_classes=[ScopedTokenPermission])
    def provenance(self, request, pk=None):
        """GET /api/patient-info/{person_id}/provenance/ — full provenance history for a patient."""
        try:
            person = Person.objects.get(person_id=pk)
            patient_info = PatientInfo.objects.get(person=person)
        except Person.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        except PatientInfo.DoesNotExist:
            return Response({'error': 'Patient information not found'}, status=status.HTTP_404_NOT_FOUND)

        org = get_request_org(request)
        if org is not None and patient_info.organization != org:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

        from django.db.models import Q
        # Build a single query for all provenance records across PatientInfo + OMOP tables
        q = Q(
            content_type=ContentType.objects.get_for_model(PatientInfo),
            object_id=patient_info.pk,
        )
        for model_cls in [Measurement, ConditionOccurrence, DrugExposure, ProcedureOccurrence]:
            omop_ids = list(model_cls.objects.filter(person_id=person.person_id).values_list('pk', flat=True))
            if omop_ids:
                q |= Q(
                    content_type=ContentType.objects.get_for_model(model_cls),
                    object_id__in=omop_ids,
                )
        records = ProvenanceRecord.objects.filter(q).select_related('content_type').order_by('-created_at')
        return Response(ProvenanceRecordSerializer(records, many=True).data)

    @action(detail=False, methods=['post'], permission_classes=[ScopedTokenPermission])
    def upload_csv(self, request):
        """Upload patients from CSV file"""
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response({'error': 'File must be a CSV'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            decoded_file = file.read().decode('utf-8')
            csv_data = StringIO(decoded_file)
            reader = csv.DictReader(csv_data)
            
            created_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    person_id = int(row.get('person_id', 0))
                    if person_id == 0:
                        last_person = Person.objects.all().order_by('-person_id').first()
                        person_id = last_person.person_id + 1 if last_person else 1000
                    
                    # Get gender concept
                    gender_concept = get_gender_concept(row.get('gender', ''))
                    gender_source = row.get('gender', 'unknown')
                    
                    person, created = Person.objects.get_or_create(
                        person_id=person_id,
                        defaults={
                            'year_of_birth': int(row.get('year_of_birth', datetime.now().year - 50)),
                            'gender_concept': gender_concept,
                            'gender_source_value': gender_source,
                            'race_concept': None,
                            'race_source_value': 'unknown',
                            'ethnicity_concept': None,
                            'ethnicity_source_value': 'unknown',
                            'person_source_value': f"CSV-{person_id}",
                        }
                    )
                    
                    date_of_birth = None
                    if row.get('date_of_birth'):
                        try:
                            date_of_birth = datetime.strptime(row['date_of_birth'], '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                date_of_birth = datetime.strptime(row['date_of_birth'], '%m/%d/%Y').date()
                            except ValueError:
                                pass
                    
                    patient_info, pi_created = PatientInfo.objects.update_or_create(
                        person=person,
                        defaults={
                            'date_of_birth': date_of_birth,
                            'disease': row.get('disease', ''),
                        }
                    )
                    
                    if pi_created:
                        created_count += 1
                        
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return Response({
                'success': True,
                'created_count': created_count,
                'errors': errors
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[ScopedTokenPermission])
    def upload_fhir(self, request):
        """Trigger async FHIR Bundle ingestion via the healthkey-etl Airflow DAG.

        The view validates the request, then hands the parsing + OMOP writes
        off to the `fhir_ingest` DAG. Returns 202 Accepted with the assigned
        `dag_run_id` so the caller can poll Airflow for status.
        """
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        if not file.name.endswith('.json'):
            return Response({'error': 'File must be a JSON file'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            fhir_data = json.load(file)
        except json.JSONDecodeError as e:
            return Response({'error': f'Invalid JSON: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(fhir_data, dict) or fhir_data.get('resourceType') != 'Bundle':
            return Response({'error': 'FHIR file must be a Bundle'}, status=status.HTTP_400_BAD_REQUEST)

        prov_source, prov_user_id, prov_reason = _extract_provenance(request)
        if prov_source == 'ADMIN_CORRECTION' and not prov_reason:
            return Response(
                {'error': 'modification_reason is required when source is ADMIN_CORRECTION'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org = get_request_org(request)

        if not settings.AIRFLOW_URL:
            return Response(
                {'error': 'AIRFLOW_URL is not configured on this server'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        conf = {
            'bundle': fhir_data,
            'fhir_version': 'r4',
            'provenance_source': prov_source,
            'provenance_source_user_id': str(prov_user_id) if prov_user_id else '',
            'provenance_target_patient_id': None,
            'provenance_organization_id': org.id if org else None,
            'provenance_modification_reason': prov_reason,
        }

        client = AirflowClientImplementation(
            airflow_url=settings.AIRFLOW_URL,
            airflow_username=settings.AIRFLOW_USERNAME,
            airflow_password=settings.AIRFLOW_PASSWORD,
        )
        dag_run_prefix = f"upload-org{org.id}" if org else "upload-noorg"
        try:
            dag_run_id = client.create_dag_run(
                dag=AirflowDag.FHIR_INGEST,
                dag_run_prefix=dag_run_prefix,
                conf=conf,
            )
        except AirflowError as e:
            return Response(
                {'error': f'Failed to schedule FHIR ingestion: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'success': True,
                'status': 'scheduled',
                'dag_id': AirflowDag.FHIR_INGEST.value,
                'dag_run_id': dag_run_id,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=['delete'], permission_classes=[ScopedTokenPermission])
    def bulk_delete(self, request):
        """Delete multiple patients by person_ids"""
        person_ids = request.data.get('person_ids', [])
        
        if not person_ids:
            return Response({'error': 'No person_ids provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            deleted_count = 0
            errors = []
            
            for person_id in person_ids:
                try:
                    person = Person.objects.get(person_id=person_id)
                    # Delete PatientInfo
                    PatientInfo.objects.filter(person=person).delete()
                    # Delete associated User if exists
                    try:
                        User.objects.filter(id=person_id).delete()
                    except User.DoesNotExist:
                        pass
                    # Delete Person
                    person.delete()
                    deleted_count += 1
                except Person.DoesNotExist:
                    errors.append(f"Person {person_id} not found")
                except Exception as e:
                    errors.append(f"Person {person_id}: {str(e)}")
            
            return Response({
                'success': True,
                'deleted_count': deleted_count,
                'errors': errors
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Simple login with username and password"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({
                'error': 'Username and password required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            user_serializer = UserSerializer(user)
            return Response({
                'message': 'Login successful',
                'user': user_serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        import traceback
        logger.error('Login error: %s\n%s', str(e), traceback.format_exc())
        return Response({
            'error': 'Login failed',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    """Logout the user and clear session"""
    logout(request)
    return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for monitoring"""
    from django.db import connection
    try:
        connection.ensure_connection()
        db_status = 'connected'
    except Exception:
        db_status = 'error'

    http_status = 200 if db_status == 'connected' else 503
    return JsonResponse({
        'status': 'healthy' if db_status == 'connected' else 'unhealthy',
        'service': 'ctomop',
        'database': db_status,
    }, status=http_status)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def auth_test(request):
    """Test auth endpoint to diagnose login 500"""
    import traceback as tb
    try:
        step = 'start'
        username = request.data.get('username', 'test')
        step = 'got username'
        from django.contrib.auth import authenticate as do_auth
        step = 'imported authenticate'
        user = do_auth(request, username=username, password='badpassword_test_only')
        step = 'authenticate done'
        return Response({'status': 'ok', 'step': step, 'user': str(user)})
    except Exception as e:
        return Response({'status': 'error', 'step': step, 'error': str(e), 'traceback': tb.format_exc()}, status=500)

# =============================================================================
# OMOP clinical event ViewSets
# =============================================================================

def _next_pk(model, pk_field):
    """Return max(pk_field) + 1, or 1 if the table is empty."""
    last = model.objects.order_by(f'-{pk_field}').values_list(pk_field, flat=True).first()
    return (last + 1) if last else 1


_MODEL_PK_MAP = {
    'ConditionOccurrence': ('condition_occurrence_id', ConditionOccurrence),
    'DrugExposure':        ('drug_exposure_id',        DrugExposure),
    'Measurement':         ('measurement_id',          Measurement),
    'Observation':         ('observation_id',          Observation),
    'ProcedureOccurrence': ('procedure_occurrence_id', ProcedureOccurrence),
}


class _OmopFilterMixin:
    """Filter by person_id query param and restrict to the requesting org's patients."""
    def get_queryset(self):
        qs = super().get_queryset()
        person_id = self.request.query_params.get('person_id')
        if person_id:
            qs = qs.filter(person_id=person_id)
        org = get_request_org(self.request)
        if org is not None:
            from omop_core.models import PatientInfo
            allowed = PatientInfo.objects.filter(organization=org).values_list('person_id', flat=True)
            qs = qs.filter(person_id__in=allowed)
        return qs


class _ProvenanceMixin:
    """Record provenance on create/update when source headers/body fields are present."""
    def _prov(self, obj):
        source, user_id, reason = _extract_provenance(self.request)
        if source:
            _record_provenance(obj, source, user_id, modification_reason=reason, organization=get_request_org(self.request))

    def perform_create(self, serializer):
        # Auto-generate PK if not supplied
        model_name = serializer.Meta.model.__name__
        if model_name in _MODEL_PK_MAP:
            pk_field, model_cls = _MODEL_PK_MAP[model_name]
            if pk_field not in serializer.validated_data:
                serializer.validated_data[pk_field] = _next_pk(model_cls, pk_field)

        # Org-scoping: reject cross-org writes
        org = get_request_org(self.request)
        if org is not None:
            person = serializer.validated_data.get('person')
            if person:
                if not PatientInfo.objects.filter(person=person, organization=org).exists():
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('Person does not belong to your organization.')

        obj = serializer.save()
        self._prov(obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        self._prov(obj)


@method_decorator(csrf_exempt, name='dispatch')
class ConditionOccurrenceViewSet(_ProvenanceMixin, _OmopFilterMixin, viewsets.ModelViewSet):
    serializer_class = ConditionOccurrenceSerializer
    permission_classes = [ScopedTokenPermission]
    queryset = ConditionOccurrence.objects.all()


@method_decorator(csrf_exempt, name='dispatch')
class DrugExposureViewSet(_ProvenanceMixin, _OmopFilterMixin, viewsets.ModelViewSet):
    serializer_class = DrugExposureSerializer
    permission_classes = [ScopedTokenPermission]
    queryset = DrugExposure.objects.all()


@method_decorator(csrf_exempt, name='dispatch')
class MeasurementViewSet(_ProvenanceMixin, _OmopFilterMixin, viewsets.ModelViewSet):
    serializer_class = MeasurementSerializer
    permission_classes = [ScopedTokenPermission]
    queryset = Measurement.objects.all()


@method_decorator(csrf_exempt, name='dispatch')
class ObservationViewSet(_ProvenanceMixin, _OmopFilterMixin, viewsets.ModelViewSet):
    serializer_class = ObservationSerializer
    permission_classes = [ScopedTokenPermission]
    queryset = Observation.objects.all()


@method_decorator(csrf_exempt, name='dispatch')
class ProcedureOccurrenceViewSet(_ProvenanceMixin, _OmopFilterMixin, viewsets.ModelViewSet):
    serializer_class = ProcedureOccurrenceSerializer
    permission_classes = [ScopedTokenPermission]
    queryset = ProcedureOccurrence.objects.all()


@method_decorator(csrf_exempt, name='dispatch')
class EpisodeViewSet(_ProvenanceMixin, _OmopFilterMixin, viewsets.ModelViewSet):
    serializer_class = EpisodeSerializer
    permission_classes = [ScopedTokenPermission]
    queryset = Episode.objects.all()


@method_decorator(csrf_exempt, name='dispatch')
class EpisodeEventViewSet(viewsets.ModelViewSet):
    serializer_class = EpisodeEventSerializer
    permission_classes = [ScopedTokenPermission]

    def get_queryset(self):
        episode_id = self.request.query_params.get('episode_id')
        qs = EpisodeEvent.objects.all()
        if episode_id:
            qs = qs.filter(episode_id=episode_id)
        return qs


# =============================================================================
# Controlled vocabulary endpoints
# GET /api/vocabularies/<model_name>/ → [{code, title}, ...]
# =============================================================================

_VOCABULARY_REGISTRY = {
    'ethnicity':                     Ethnicity,
    'stem-cell-transplant':          StemCellTransplant,
    'histologic-type':               HistologicType,
    'estrogen-receptor-status':      EstrogenReceptorStatus,
    'progesterone-receptor-status':  ProgesteroneReceptorStatus,
    'her2-status':                   Her2Status,
    'hr-status':                     HrStatus,
    'hrd-status':                    HrdStatus,
    'mutation-origin':               MutationOrigin,
    'mutation-gene':                 MutationGene,
    'mutation-interpretation':       MutationInterpretation,
    'mutation-code':                 MutationCode,
    'tumor-stage':                   TumorStage,
    'nodes-stage':                   NodesStage,
    'distant-metastasis-stage':      DistantMetastasisStage,
    'staging-modality':              StagingModality,
    'toxicity-grade':                ToxicityGrade,
    'language':                      Language,
    'language-skill-level':          LanguageSkillLevel,
    'binet-stage':                   BinetStage,
    'protein-expression':            ProteinExpression,
    'richter-transformation':        RichterTransformation,
    'tumor-burden':                  TumorBurden,
    'morphologic-variant':           MorphologicVariant,
    'disease-activity':              DiseaseActivity,
    'pre-existing-condition-category': PreExistingConditionCategory,
    'disease':                         Disease,
    'cancer-stage':                    CancerStage,
    'karnofsky-score':                 KarnofskyScore,
    'ecog-status':                     EcogStatus,
    'peripheral-neuropathy-grade':     PeripheralNeuropathyGrade,
    'infection-status':                InfectionStatus,
    'disease-progression':             DiseaseProgression,
    'measurable-disease':              MeasurableDisease,
    'gelf-criteria':                   GelfCriteria,
    'flipi-score':                     FlipIScore,
    'follicular-lymphoma-grade':             FollicularLymphomaGrade,
    'breast-cancer-first-line-therapy':      BreastCancerFirstLineTherapy,
    'breast-cancer-second-line-therapy':     BreastCancerSecondLineTherapy,
    'breast-cancer-later-line-therapy':      BreastCancerLaterLineTherapy,
}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vocabulary_list(request, model_name):
    """Return all entries for a controlled vocabulary model as [{code, title}]."""
    model = _VOCABULARY_REGISTRY.get(model_name)
    if model is None:
        return Response(
            {'error': f"Unknown vocabulary '{model_name}'. Valid options: {sorted(_VOCABULARY_REGISTRY.keys())}"},
            status=status.HTTP_404_NOT_FOUND,
        )
    has_sort_key = any(f.name == 'sort_key' for f in model._meta.get_fields())
    order_field = 'sort_key' if has_sort_key else 'title'
    items = list(model.objects.values('code', 'title', 'source_name', 'source_url').order_by(order_field))
    return Response(items)


# =============================================================================
# HealthTree parity ViewSets
# =============================================================================

@method_decorator(csrf_exempt, name='dispatch')
class PatientDocumentViewSet(_OmopFilterMixin, viewsets.ModelViewSet):
    serializer_class = PatientDocumentSerializer
    permission_classes = [ScopedTokenPermission]
    queryset = PatientDocument.objects.all()


class PatientTrialEnrollmentViewSet(_OmopFilterMixin, viewsets.ModelViewSet):
    """CRUD for a patient's clinical trial enrollment status.

    Trial metadata (title, phase, eligibility, etc.) is NOT stored here.
    Use ``trial_id`` to retrieve that data from the EXACT trial-matcher API.

    Filter by person: GET /api/trial-enrollments/?person_id=42
    """
    serializer_class = PatientTrialEnrollmentSerializer
    permission_classes = [ScopedTokenPermission]
    queryset = PatientTrialEnrollment.objects.all()
