"""PatientRecord-first cytogenetic marker authoring and refresh coverage."""

from importlib import import_module
from unittest.mock import patch

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from omop_core.models import (
    Concept, FieldChoice, FieldChoiceCode, FieldConceptMapping, Observation, PatientRecord,
)
from omop_core.services.cytogenetics import normalise_cytogenetic_markers
from omop_core.services.write_descriptor import KIND_DIRECT, build_writable_field_descriptor
from tests.factories import ConceptFactory, DomainFactory, PatientRecordFactory, VocabularyFactory


pytestmark = pytest.mark.django_db


def _cytogenetic_concept():
    import_module('omop_core.migrations.0077_seed_concept_zero').seed_concept_zero(apps, None)
    return Concept.objects.get(pk=0)


def _approved_mapping(concept):
    return FieldConceptMapping.objects.create(
        field_name='cytogenetic_markers',
        concept=concept,
        vocabulary_id='',
        concept_code='',
        omop_table='observation',
        source_value='mm-cytogenetic-markers',
        value_kind='string',
        multiple=True,
        status='approved',
    )


def test_normalises_ui_and_import_spellings_without_losing_unknown_import_data():
    assert normalise_cytogenetic_markers(
        'del(17p13), 1q21 amplification, DEL17P, MYC rearrangement'
    ) == 'del17p, 1q_amp, MYC rearrangement'
    assert normalise_cytogenetic_markers('future-marker') == 'future-marker'
    with pytest.raises(ValueError, match='future-marker'):
        normalise_cytogenetic_markers('future-marker', strict=True)


def test_seed_is_explicit_under_pytest_no_migrations():
    """Exercise seed logic directly because pytest.ini uses --no-migrations."""
    _cytogenetic_concept()
    migration = import_module('omop_core.migrations.0222_cytogenetic_markers')

    migration.migrate_and_seed(apps, None)

    choices = {
        choice.display: choice
        for choice in FieldChoice.objects.filter(field_name='cytogenetic_markers')
    }
    assert set(migration.CHOICES)  # the frozen migration owns the deployed value set
    assert {'del17p', 't(4;14)', 't(11;14)', '1q_amp', 'hyperdiploidy',
            'MYC rearrangement'} <= choices.keys()
    assert not FieldChoiceCode.objects.filter(choice__field_name='cytogenetic_markers').exists()
    mapping = FieldConceptMapping.objects.get(field_name='cytogenetic_markers')
    assert mapping.status == 'approved'
    assert mapping.concept_id == 0
    assert mapping.vocabulary_id == mapping.concept_code == ''
    assert mapping.source_value == 'mm-cytogenetic-markers'
    assert mapping.multiple is True


def test_approved_mapping_exposes_choices_on_patientrecord_descriptor():
    concept = _cytogenetic_concept()
    _approved_mapping(concept)
    choice = FieldChoice.objects.create(
        field_name='cytogenetic_markers', display='del17p', sort_order=0,
    )
    entry = build_writable_field_descriptor()['cytogenetic_markers']

    assert entry['kind'] == KIND_DIRECT
    assert entry['target'] == 'patient_record'
    assert entry['multiple'] is True
    assert entry['options'] == [{'value': 'del17p', 'code': None}]
    assert entry['projection']['omop_table'] == 'observation'
    assert entry['projection']['source_value'] == 'mm-cytogenetic-markers'


def test_patch_persists_patientrecord_then_projects_without_refresh_and_import_refreshes():
    concept = _cytogenetic_concept()
    ConceptFactory(concept_id=32817, concept_code='32817', concept_name='EHR type')
    _approved_mapping(concept)
    record = PatientRecordFactory(disease='multiple myeloma')
    user = get_user_model().objects.create_user(
        email='cytogenetics-admin@example.test', password='test', is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    with patch('omop_core.services.patient_record_service.refresh_patient_record') as refresh:
        response = client.patch(
            f'/api/patient-info/{record.person_id}/',
            {'cytogenetic_markers': 'del(17p13), 1q21 amplification'},
            format='json',
        )

    assert response.status_code == 200, response.data
    refresh.assert_not_called()
    record.refresh_from_db()
    assert record.cytogenetic_markers == 'del17p, 1q_amp'
    assert 'cytogenetic_markers' not in (record.user_edited_fields or [])
    observation = Observation.objects.get(
        person=record.person,
        observation_concept=concept,
        observation_source_value='mm-cytogenetic-markers',
    )
    assert observation.value_as_string == 'del17p, 1q_amp'

    # An external/imported OMOP change takes the opposite direction and invokes
    # the normal full refresh back into PatientRecord.
    observation.value_as_string = 'FGFR3/IGH translocation t(4;14), del(17p13)'
    observation.save(update_fields=['value_as_string'])
    record.refresh_from_db()
    assert record.cytogenetic_markers == 't(4;14), del17p'


def test_serializer_rejects_values_outside_the_ui_vocabulary():
    record = PatientRecordFactory(disease='multiple myeloma')
    from patient_portal.api.serializers import PatientRecordSerializer

    serializer = PatientRecordSerializer(
        record, data={'cytogenetic_markers': 'not-a-reviewed-marker'}, partial=True,
    )
    assert serializer.is_valid() is False
    assert 'cytogenetic_markers' in serializer.errors


def test_serializer_accepts_the_legacy_write_name_but_emits_only_the_canonical_name():
    record = PatientRecordFactory(disease='multiple myeloma')
    from patient_portal.api.serializers import PatientRecordSerializer

    serializer = PatientRecordSerializer(
        record, data={'cytogenic_markers': 'del(17p13)'}, partial=True,
    )
    assert serializer.is_valid(), serializer.errors
    saved = serializer.save()
    assert saved.cytogenetic_markers == 'del17p'
    representation = PatientRecordSerializer(saved).data
    assert representation['cytogenetic_markers'] == 'del17p'
    assert 'cytogenic_markers' not in representation


def test_repair_removes_wrong_codes_without_changing_1204_status_or_curated_choices():
    from tests.factories import ObservationFactory

    _cytogenetic_concept()
    status_concept = ConceptFactory(
        concept_code='69548-6', concept_name='Genetic variant assessment',
        vocabulary=VocabularyFactory(vocabulary_id='LOINC'),
        domain=DomainFactory(domain_id='Measurement', domain_name='Measurement'),
    )
    summary = FieldConceptMapping.objects.create(
        field_name='cytogenetic_markers', concept=status_concept,
        vocabulary_id='LOINC', concept_code='69548-6', omop_table='observation',
        source_value='mm-cytogenetic-markers', value_kind='string', status='approved',
    )
    status = FieldConceptMapping.objects.create(
        field_name='genetic_mutations.status', concept=status_concept,
        vocabulary_id='LOINC', concept_code='69548-6', omop_table='measurement',
        source_value='genomics:status', value_kind='string', status='approved',
    )
    choice = FieldChoice.objects.create(field_name='cytogenetic_markers', display='1q_amp')
    bad = FieldChoiceCode.objects.create(choice=choice, vocabulary_id='LOINC', code='81249-5')
    curated = FieldChoiceCode.objects.create(choice=choice, vocabulary_id='Local', code='1q_amp')
    # This was written by an earlier development version of the summary seed.
    wrong_fact = ObservationFactory(
        observation_concept=status_concept, observation_source_value='mm-cytogenetic-markers',
        value_as_string='1q_amp',
    )
    separate_status = ObservationFactory(
        observation_concept=status_concept, observation_source_value='genomics:status',
        value_as_string='present',
    )
    migration = import_module('omop_core.migrations.0225_merge_cytogenetic_markers')
    migration.correct_cytogenetic_codes(apps, None)
    migration.correct_cytogenetic_codes(apps, None)
    summary.refresh_from_db()
    status.refresh_from_db()
    wrong_fact.refresh_from_db()
    separate_status.refresh_from_db()
    assert summary.concept_id == wrong_fact.observation_concept_id == 0
    assert wrong_fact.value_as_string == '1q_amp'
    assert summary.concept_code == summary.vocabulary_id == ''
    assert status.concept_id == status_concept.pk
    assert status.omop_table == 'measurement'
    assert status.concept_code == '69548-6'
    assert separate_status.observation_concept_id == status_concept.pk
    assert not FieldChoiceCode.objects.filter(pk=bad.pk).exists()
    assert FieldChoiceCode.objects.filter(pk=curated.pk).exists()


def test_seed_preserves_a_curator_supplied_summary_recipe():
    concept = ConceptFactory()
    mapping = _approved_mapping(concept)
    import_module('omop_core.migrations.0222_cytogenetic_markers').migrate_and_seed(apps, None)
    mapping.refresh_from_db()
    assert mapping.concept_id == concept.pk
