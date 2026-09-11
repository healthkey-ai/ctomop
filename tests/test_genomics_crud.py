"""Genomics UI/API → OMOP → projection; isolation and lossless round trips."""
import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from omop_core.models import Concept, Measurement, Observation
from omop_core.services.genomics import FIELDS, list_variants, replace_variants, save_variant
from omop_core.services.patient_record_service import refresh_patient_record
from patient_portal.api.views import PatientRecordViewSet
from patient_portal.models import Identity, PatientUser
from tests.factories import ConceptFactory, MeasurementFactory, ObservationFactory, PatientRecordFactory, PersonFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    person = PersonFactory()
    record = PatientRecordFactory(person=person)
    ConceptFactory(vocabulary__vocabulary_id='CDM', concept_code='measurement.measurement_id')
    for field, (code, domain) in FIELDS.items():
        if not code.startswith('genomics:'):
            ConceptFactory(concept_code=code, domain__domain_id=domain)
    ConceptFactory(concept_code='81252-9')
    from django.core.management import call_command
    call_command('seed_genomics_catalog')
    staff = Identity.objects.create_user(email='genomics@example.test', password='pw', is_staff=True)
    return person, record, staff


def call(person, user, method, payload=None, variant_id=None):
    name = 'genomics' if variant_id is None else 'genomic_variant'
    request = getattr(APIRequestFactory(), method)(f'/api/v1/patient-records/{person.pk}/genomics/', payload, format='json')
    force_authenticate(request, user=user)
    kwargs = {'pk': str(person.pk)}
    if variant_id is not None:
        kwargs['variant_id'] = str(variant_id)
    return PatientRecordViewSet.as_view({method: name}, **getattr(PatientRecordViewSet, name).kwargs)(request, **kwargs)


def test_full_crud_preserves_all_fields_and_unrelated_facts(setup):
    person, record, staff = setup
    payload = {
        'gene': 'BRCA1', 'variant': 'NM_007294.4:c.68_69delAG',
        'variant_name': '185delAG', 'variant_description': 'Original laboratory narrative. ' * 20,
        'origin': 'germline', 'interpretation': 'Likely pathogenic',
        'test_date': '2026-09-01', 'genome_assembly': 'GRCh38',
        'transcript_reference_sequence_id': 'NM_007294.4',
        'amino_acid_change': 'p.Glu23ValfsTer17', 'variant_category': 'Simple variant',
        'variant_analysis_method_type': 'NGS', 'genomic_source_class': 'Germline',
        'chromosome': '17', 'cytogenetic_location': '17q21.31',
        'genomic_dna_change': 'NC_000017.11:g.43124027_43124028del',
        'allelic_frequency': 43.25, 'allelic_frequency_unit': '%',
    }
    unrelated = MeasurementFactory(person=person, value_as_string='Unrelated lab')
    response = call(person, staff, 'post', payload)
    assert response.status_code == 201, response.data
    variant_id = response.data['id']
    assert {k: response.data[k] for k in payload} == payload
    parent = Measurement.objects.get(pk=variant_id)
    assert parent.measurement_source_value == 'genomics:brca1'
    assert Observation.objects.get(person=person, observation_source_value='genomics:variant_description').value_as_string == payload['variant_description']
    frequency = Measurement.objects.get(person=person, measurement_source_value='81258-6')
    assert float(frequency.value_as_number) == 43.25
    assert frequency.unit_source_value == '%'
    assert frequency.measurement_event_id == variant_id
    refresh_patient_record(person)
    record.refresh_from_db()
    assert record.genetic_mutations == [response.data]
    assert call(person, staff, 'get').data == [response.data]
    assert call(person, staff, 'get', variant_id=variant_id).data == response.data

    second = call(person, staff, 'post', {**payload, 'allelic_frequency': 0})
    assert second.status_code == 201
    assert second.data['id'] != variant_id  # repeat gene / variant is a distinct test
    edited = call(person, staff, 'patch', {'amino_acid_change': '', 'allelic_frequency': 0.5, 'allelic_frequency_unit': '1'}, variant_id)
    assert edited.status_code == 200, edited.data
    assert edited.data['id'] == variant_id
    assert edited.data.get('amino_acid_change') in ('', None)
    assert edited.data['variant_description'] == payload['variant_description']
    assert edited.data['allelic_frequency'] == 0.5
    assert call(person, staff, 'delete', variant_id=variant_id).status_code == 204
    assert [v['id'] for v in list_variants(person)] == [second.data['id']]
    assert Measurement.objects.get(pk=variant_id).is_erroneous
    assert not Measurement.objects.get(pk=unrelated.pk).is_erroneous
    assert not Measurement.objects.filter(person=person, measurement_event_id=variant_id, is_erroneous=False).exists()
    assert not Observation.objects.filter(person=person, observation_event_id=variant_id, is_erroneous=False).exists()
    assert call(person, staff, 'get', variant_id=variant_id).status_code == 404


@pytest.mark.parametrize('bad', [
    {'gene': ''}, {'gene': {}}, {'test_date': '2026-02-30'},
    {'allelic_frequency': -1}, {'allelic_frequency': 101},
    {'allelic_frequency': 'NaN'}, {'allelic_frequency': True},
    {'allelic_frequency': 0.123456}, {'allelic_frequency_unit': 'ppm'},
    {'allelic_frequency': 10, 'allelic_frequency_unit': '1'},
    {'variant_name': ['invalid']}, {'unknown_field': 'lost data'},
])
def test_invalid_data_cannot_partially_write(setup, bad):
    person, _, staff = setup
    response = call(person, staff, 'post', {'gene': 'TP53', **bad})
    assert response.status_code == 400, response.data
    assert not Measurement.objects.filter(person=person).exists()
    assert not Observation.objects.filter(person=person).exists()


def test_imported_variant_can_be_updated_without_duplicate(setup):
    person, _, staff = setup
    old = MeasurementFactory(person=person, measurement_source_value='21636-6', value_as_string='c.123A>G')
    response = call(person, staff, 'patch', {'gene': 'TP53', 'genome_assembly': 'GRCh38'}, old.pk)
    assert response.status_code == 200, response.data
    assert response.data['gene'] == 'TP53'
    assert response.data['variant'] == 'c.123A>G'
    assert [v['id'] for v in list_variants(person)] == [old.pk]


def test_cross_patient_variant_ids_are_rejected(setup):
    person, _, staff = setup
    other = PersonFactory()
    PatientRecordFactory(person=other)
    variant = save_variant(other, {'gene': 'TP53'})
    for method in ('get', 'patch', 'delete'):
        response = call(person, staff, method, {'gene': 'BRCA1'}, variant['id'])
        assert response.status_code == 404
    assert len(list_variants(other)) == 1


def test_unrelated_user_cannot_read_or_write(setup):
    person, _, _ = setup
    outsider = Identity.objects.create_user(email='outsider@example.test', password='pw')
    for method in ('get', 'post'):
        assert call(person, outsider, method, {'gene': 'TP53'}).status_code == 404


def test_patient_can_crud_own_record(setup):
    person, _, _ = setup
    patient = Identity.objects.create_user(email='self@example.test', password='pw')
    PatientUser.objects.create(identity=patient, person=person)
    ConceptFactory(concept_id=32865)
    response = call(person, patient, 'post', {'gene': 'TP53'})
    assert response.status_code == 201, response.data
    assert Measurement.objects.get(pk=response.data['id']).measurement_type_concept_id == 32865
    assert call(person, patient, 'delete', variant_id=response.data['id']).status_code == 204


def test_standard_observation_domain_is_respected(setup):
    person, _, _ = setup
    from tests.factories import DomainFactory
    domain = DomainFactory(domain_id='Observation')
    Concept.objects.filter(concept_code='53037-8').update(domain=domain)
    from omop_core.models import FieldConceptMapping
    FieldConceptMapping.objects.filter(field_name='genetic_mutations.interpretation').update(omop_table='observation')
    result = save_variant(person, {'gene': 'TP53', 'interpretation': 'VUS'})
    row = Observation.objects.get(person=person, observation_source_value='53037-8')
    assert row.observation_concept.domain_id == 'Observation'
    assert row.observation_event_id == result['id']
    assert result['interpretation'] == 'VUS'


def test_missing_loinc_keeps_source_code_and_unmapped_concept(setup):
    person, _, _ = setup
    from omop_core.models import FieldConceptMapping
    FieldConceptMapping.objects.filter(field_name='genetic_mutations.genome_assembly').update(concept_id=0)
    Concept.objects.filter(concept_code='62374-4').delete()
    save_variant(person, {'gene': 'TP53', 'genome_assembly': 'GRCh38'})
    row = Measurement.objects.get(person=person, measurement_source_value='62374-4')
    assert row.measurement_concept_id == 0
    assert row.value_as_string == 'GRCh38'


def test_linked_imported_gene_and_component_without_source_code(setup):
    person, _, staff = setup
    parent = MeasurementFactory(person=person, measurement_source_value='81252-9', value_as_string='c.123A>G')
    link = Concept.objects.get(vocabulary_id='CDM', concept_code='measurement.measurement_id')
    ObservationFactory(person=person, observation_concept=Concept.objects.get(concept_code='48018-6'),
        observation_event_id=parent.pk, obs_event_field_concept=link, value_as_string='BRCA2')
    amino = MeasurementFactory(person=person, measurement_concept=Concept.objects.get(concept_code='48005-3'),
        measurement_source_value=None, measurement_event_id=parent.pk, meas_event_field_concept=link,
        value_as_string='p.Gly12Val')
    assert list_variants(person)[0]['gene'] == 'BRCA2'
    result = call(person, staff, 'patch', {'amino_acid_change': ''}, parent.pk)
    assert result.status_code == 200, result.data
    assert result.data.get('amino_acid_change') in (None, '')
    amino.refresh_from_db()
    assert amino.is_erroneous


def test_legacy_list_patch_rolls_back_and_handles_empty_list(setup):
    person, _, _ = setup
    ConceptFactory(concept_id=32865)
    initial = save_variant(person, {'gene': 'TP53', 'variant': 'c.123A>G'})
    from rest_framework.exceptions import ValidationError
    with pytest.raises(ValidationError):
        replace_variants(person, [{**initial, 'gene': 'BRCA1'}, {'gene': ''}])
    assert list_variants(person) == [initial]
    replace_variants(person, [])
    assert list_variants(person) == []


def test_analyst_cannot_mutate_visible_patient(setup, monkeypatch):
    person, _, _ = setup
    analyst = Identity.objects.create_user(email='analyst@example.test', password='pw')
    monkeypatch.setattr('omop_core.authorization.can_access_patient', lambda *_: True)
    monkeypatch.setattr('omop_core.authorization.can_write_patient', lambda *_: False)
    variant = save_variant(person, {'gene': 'TP53'})
    assert call(person, analyst, 'get').status_code == 200
    for method in ('post', 'patch', 'delete'):
        response = call(person, analyst, method, {'gene': 'BRCA1'}, None if method == 'post' else variant['id'])
        assert response.status_code == 403
    assert list_variants(person) == [variant]
