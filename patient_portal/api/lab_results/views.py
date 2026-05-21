from collections import defaultdict

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from omop_core.models import (
    CareSite, Concept, LoincClass, LoincCodeClass,
    Measurement, VisitOccurrence,
)
from patient_portal.api.permissions import ScopedTokenPermission, get_request_org

from .serializers import LabResultCardSerializer

MAX_VALUES_PER_CONCEPT = 10


class LabResultsPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


def _compute_status(value, range_low, range_high):
    if value is None:
        return 'unknown'
    if range_low is not None and value < range_low:
        return 'below'
    if range_high is not None and value > range_high:
        return 'above'
    if range_low is not None or range_high is not None:
        return 'in_range'
    return 'unknown'


MEASUREMENT_TYPE_LABELS = {
    32817: 'ehr',
    32883: 'document_extraction',
    32865: 'patient_self_report',
}


def _build_category_cache():
    """Build LOINC concept_code → category display name cache."""
    class_names = dict(LoincClass.objects.values_list('code', 'display_name'))
    code_to_class = dict(LoincCodeClass.objects.values_list('loinc_num', 'loinc_class_id'))
    return {
        loinc_num: class_names[class_code]
        for loinc_num, class_code in code_to_class.items()
        if class_code in class_names
    }


class ResultsSummaryView(APIView):
    """
    GET /api/lab-results/summary/?person_id=X&page=1&page_size=50

    Returns lab results grouped by effective concept (LOINC or HK-Labs custom),
    with up to 10 most recent values per concept, category, status, and provenance.
    """
    permission_classes = [ScopedTokenPermission]

    def get(self, request):
        person_id = request.query_params.get('person_id')
        if not person_id:
            return Response(
                {'detail': 'person_id query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org = get_request_org(request)
        if org is not None:
            from omop_core.models import PatientInfo
            if not PatientInfo.objects.filter(person_id=person_id, organization=org).exists():
                return Response(
                    {'detail': 'Person not found in your organization.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        cards = self._build_cards(int(person_id))

        paginator = LabResultsPagination()
        page = paginator.paginate_queryset(cards, request)
        serializer = LabResultCardSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def _build_cards(self, person_id):
        measurements = (
            Measurement.objects
            .filter(person_id=person_id)
            .select_related(
                'measurement_concept', 'measurement_source_concept',
                'measurement_type_concept', 'unit_concept',
            )
            .order_by('-measurement_date', '-measurement_id')
        )

        concept_groups = defaultdict(list)
        for m in measurements:
            eff_id = m.measurement_concept_id
            if eff_id == 0 and m.measurement_source_concept_id:
                eff_id = m.measurement_source_concept_id
            if len(concept_groups[eff_id]) < MAX_VALUES_PER_CONCEPT:
                concept_groups[eff_id].append(m)

        if not concept_groups:
            return []

        concepts = {
            c.concept_id: c
            for c in Concept.objects.filter(concept_id__in=concept_groups.keys())
        }

        provenance = self._load_provenance(concept_groups)
        category_cache = _build_category_cache()

        cards = []
        for concept_id, meas_list in concept_groups.items():
            concept = concepts.get(concept_id)
            if not concept:
                continue

            if concept.vocabulary_id == 'LOINC':
                category = category_cache.get(concept.concept_code, 'Uncategorized')
            elif concept.vocabulary_id == 'HK-Labs':
                category = 'Uncategorized'
            else:
                category = 'Other'

            values = []
            for m in meas_list:
                s = _compute_status(m.value_as_number, m.range_low, m.range_high)

                unit_str = m.unit_source_value
                if not unit_str and m.unit_concept:
                    unit_str = m.unit_concept.concept_code

                type_label = None
                if m.measurement_type_concept_id:
                    type_label = MEASUREMENT_TYPE_LABELS.get(
                        m.measurement_type_concept_id,
                    )
                    if type_label is None and m.measurement_type_concept:
                        type_label = m.measurement_type_concept.concept_name

                lab_name = None
                report_filename = None
                if m.visit_occurrence_id:
                    prov = provenance.get(m.visit_occurrence_id)
                    if prov:
                        lab_name = prov.get('lab_name')
                        report_filename = prov.get('report_filename')

                values.append({
                    'measurement_id': m.measurement_id,
                    'value': m.value_as_number,
                    'value_string': m.value_as_string,
                    'unit': unit_str,
                    'status': s,
                    'measured_at': m.measurement_date,
                    'range_low': m.range_low,
                    'range_high': m.range_high,
                    'source': type_label,
                    'lab_name': lab_name,
                    'report_filename': report_filename,
                })

            cards.append({
                'concept_id': concept_id,
                'concept_code': concept.concept_code,
                'concept_name': concept.concept_name,
                'vocabulary_id': concept.vocabulary_id,
                'category': category,
                'values': values,
            })

        cards.sort(key=lambda c: (
            c['category'],
            -(c['values'][0]['measured_at'].toordinal() if c['values'] else 0),
        ))
        return cards

    def _load_provenance(self, concept_groups):
        """Load lab_name + report_filename for all visit_occurrence_ids referenced."""
        visit_ids = set()
        for meas_list in concept_groups.values():
            for m in meas_list:
                if m.visit_occurrence_id:
                    visit_ids.add(m.visit_occurrence_id)

        if not visit_ids:
            return {}

        visits = VisitOccurrence.objects.filter(
            visit_occurrence_id__in=visit_ids
        ).values('visit_occurrence_id', 'care_site_id', 'visit_source_value')

        care_site_ids = set()
        visit_data = {}
        for v in visits:
            visit_data[v['visit_occurrence_id']] = v
            if v['care_site_id']:
                care_site_ids.add(v['care_site_id'])

        care_site_names = {}
        if care_site_ids:
            care_site_names = dict(
                CareSite.objects.filter(care_site_id__in=care_site_ids)
                .values_list('care_site_id', 'care_site_name')
            )

        result = {}
        for vid, v in visit_data.items():
            result[vid] = {
                'lab_name': care_site_names.get(v['care_site_id']) if v['care_site_id'] else None,
                'report_filename': v['visit_source_value'],
            }
        return result
