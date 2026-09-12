"""Per-value coded observations round-trip through the PatientRecord PATCH API."""
from datetime import timedelta
from importlib import import_module
from unittest.mock import patch

import pytest
from django.apps import apps
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from omop_core.models import Concept, FieldChoiceCode, Observation
from omop_core.services.cytogenetics import FIELD, SOURCE_PREFIX, VALUES, descriptor
from omop_core.services.omop_projection import CLEAR_VALUE
from omop_core.services.patient_record_service import refresh_patient_record
from omop_core.signals import suppress_patient_record_refresh
from patient_portal.models import Identity
from tests.factories import ObservationFactory, PatientRecordFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def editor(settings):
    settings.CELERY_BROKER_URL = ''
    migration = import_module('omop_core.migrations.0228_cytogenetic_marker_choices')
    with connection.schema_editor() as schema_editor:
        migration.seed(apps, schema_editor)
    record = PatientRecordFactory()
    client = APIClient()
    client.force_authenticate(Identity.objects.create_user(email='cytogenetics@example.test', is_staff=True))
    return record, client


def save(editor, value):
    record, client = editor
    response = client.patch(f'/api/patient-info/{record.person_id}/', {FIELD: value}, format='json')
    assert response.status_code == 200, response.data
    record.refresh_from_db()
    return response


@pytest.mark.parametrize('marker', VALUES)
def test_every_choice_creates_its_mapped_standard_observation(editor, marker):
    record, _ = editor
    save(editor, [marker])
    row = Observation.objects.get(person=record.person)
    mapping = FieldChoiceCode.objects.get(choice__field_name=FIELD, choice__display=marker, is_primary=True)
    assert row.observation_concept.concept_code == mapping.code
    assert row.observation_concept.vocabulary_id == mapping.vocabulary_id
    assert row.observation_concept.standard_concept == 'S'
    assert row.observation_concept.domain_id == 'Observation'
    assert row.observation_source_value == SOURCE_PREFIX + marker
    assert row.value_as_string == marker
    assert FIELD not in record.user_edited_fields
    assert refresh_patient_record(record.person).cytogenic_markers == marker


def test_multiple_choices_sharing_a_concept_are_distinct_and_repeat_save_is_idempotent(editor):
    record, _ = editor
    save(editor, ['t(4;14)', 't(11;14)', 't(14;16)'])
    rows = Observation.objects.filter(person=record.person)
    assert rows.count() == 3
    assert len(set(rows.values_list('observation_concept_id', flat=True))) == 1
    save(editor, 't(4;14), t(11;14), t(14;16)')
    assert rows.count() == 3
    assert refresh_patient_record(record.person).cytogenic_markers == 't(4;14), t(11;14), t(14;16)'


def test_deselection_and_clear_preserve_history_and_survive_refresh(editor):
    record, _ = editor
    yesterday = timezone.localdate() - timedelta(days=1)
    with patch('django.utils.timezone.localdate', return_value=yesterday):
        save(editor, ['t(4;14)', 't(11;14)'])
    save(editor, ['t(11;14)'])
    assert refresh_patient_record(record.person).cytogenic_markers == 't(11;14)'
    assert Observation.objects.filter(person=record.person, observation_date=yesterday,
                                      value_as_string__isnull=False).count() == 2
    cleared = Observation.objects.get(person=record.person, observation_date=timezone.localdate(),
                                      observation_source_value=SOURCE_PREFIX + 't(4;14)')
    assert cleared.value_source_value == CLEAR_VALUE
    save(editor, [])
    assert refresh_patient_record(record.person).cytogenic_markers == ''
    save(editor, ['t(4;14)'])
    assert refresh_patient_record(record.person).cytogenic_markers == 't(4;14)'


def test_legacy_import_normalization_and_clearing(editor):
    record, _ = editor
    with suppress_patient_record_refresh():
        ObservationFactory(person=record.person,
            observation_concept=Concept.objects.get(concept_code='107675007', vocabulary_id='SNOMED'),
            observation_date=timezone.localdate() - timedelta(days=1),
            observation_source_value='mm-cytogenetic-markers',
            value_as_string='del17p,t(4,14),1q_amp')
    assert refresh_patient_record(record.person).cytogenic_markers == 'del(17p13), t(4;14), 1q21 amplification'
    save(editor, ['1q_amp'])
    assert refresh_patient_record(record.person).cytogenic_markers == '1q21 amplification'
    save(editor, None)
    assert not refresh_patient_record(record.person).cytogenic_markers


def test_newer_external_marker_updates_record(editor):
    record, _ = editor
    save(editor, ['t(4;14)'])
    with suppress_patient_record_refresh():
        ObservationFactory(person=record.person,
            observation_concept=Concept.objects.get(concept_code='55597007', vocabulary_id='SNOMED'),
            observation_date=timezone.localdate() + timedelta(days=1),
            observation_source_value=SOURCE_PREFIX + 'hyperdiploidy', value_as_string='hyperdiploidy')
    assert refresh_patient_record(record.person).cytogenic_markers == 't(4;14), hyperdiploidy'


def test_invalid_or_wrong_domain_concept_never_projects_a_partial_selection(editor):
    record, _ = editor
    Concept.objects.filter(concept_code='55597007', vocabulary_id='SNOMED').update(standard_concept=None)
    save(editor, ['t(4;14)', 'hyperdiploidy'])
    assert not Observation.objects.filter(person=record.person).exists()
    assert FIELD in record.user_edited_fields
    assert refresh_patient_record(record.person).cytogenic_markers == 't(4;14), hyperdiploidy'


def test_partial_failure_rolls_back_every_marker_and_preserves_edit(editor):
    from omop_core.services.omop_projection import project_single_value
    record, _ = editor
    def fail_second(person, field, value, recipe, **kwargs):
        if recipe.get('source_value') == SOURCE_PREFIX + 't(11;14)':
            return False
        return project_single_value(person, field, value, recipe, **kwargs)
    with patch('omop_core.services.omop_projection.project_single_value', side_effect=fail_second):
        save(editor, ['t(4;14)', 't(11;14)'])
    assert not Observation.objects.filter(person=record.person).exists()
    assert FIELD in record.user_edited_fields


def test_descriptor_exposes_all_codes_and_migration_is_idempotent(editor):
    migration = import_module('omop_core.migrations.0228_cytogenetic_marker_choices')
    with connection.schema_editor() as schema_editor:
        migration.seed(apps, schema_editor)
    entry = descriptor()
    assert entry['multiple'] is True
    assert [o['value'] for o in entry['options']] == list(VALUES)
    assert all(o['concept_id'] and o['code'] for o in entry['options'])
    assert set(entry['projection']['choice_projections']) == set(VALUES)


@pytest.mark.parametrize('value', [['not a marker'], {'marker': 'del17p'}, [1]])
def test_invalid_selections_are_rejected(editor, value):
    record, client = editor
    response = client.patch(f'/api/patient-info/{record.person_id}/', {FIELD: value}, format='json')
    assert response.status_code == 400
    assert not Observation.objects.filter(person=record.person).exists()
