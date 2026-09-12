"""Existing automatic proposals must not suppress the approved summary recipe."""
from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils import timezone
import pytest

from omop_core.models import FieldConceptMapping
from omop_core.services.write_descriptor import build_writable_field_descriptor
from tests.factories import ConceptFactory, DomainFactory, VocabularyFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def proposal():
    import_module('omop_core.migrations.0077_seed_concept_zero').seed_concept_zero(apps, None)
    concept = ConceptFactory(
        concept_code='55232-3', vocabulary=VocabularyFactory(vocabulary_id='LOINC'),
        domain=DomainFactory(domain_id='Observation', domain_name='Observation'),
    )
    mapping = FieldConceptMapping.objects.create(
        field_name='cytogenetic_markers', concept=concept, vocabulary_id='LOINC',
        concept_code='55232-3', omop_table='Observation', status='proposed',
        notes='Auto-proposed from field suggestion.',
    )
    # Reproduce the upgrade path: the original rename seeds choices but keeps
    # this pre-existing proposal because a mapping already exists.
    import_module('omop_core.migrations.0222_cytogenetic_markers').migrate_and_seed(apps, None)
    return mapping


def repair():
    import_module('omop_core.migrations.0230_repair_automatic_cytogenetic_proposal').repair_automatic_proposal(apps, None)


def test_legacy_auto_proposal_becomes_an_idempotent_writable_summary(proposal):
    repair()
    proposal.refresh_from_db()
    assert proposal.concept_id == 0
    assert proposal.vocabulary_id == proposal.concept_code == ''
    assert proposal.status == 'approved'
    assert proposal.provenance == 'system_generated'
    descriptor = build_writable_field_descriptor()['cytogenetic_markers']
    assert descriptor['projection']['concept_id'] == 0
    assert descriptor['projection']['source_value'] == 'mm-cytogenetic-markers'
    assert descriptor['multiple'] is True
    updated_at = proposal.updated_at
    repair()
    proposal.refresh_from_db()
    assert proposal.updated_at == updated_at


@pytest.mark.parametrize('decision', ['approved', 'rejected', 'reviewed', 'curator_draft', 'custom_recipe'])
def test_curator_decisions_and_custom_recipes_are_preserved(proposal, decision):
    if decision in ('approved', 'rejected'):
        proposal.status = decision
    elif decision == 'reviewed':
        proposal.reviewer = get_user_model().objects.create_user(email='curator@example.test')
        proposal.reviewed_at = timezone.now()
    elif decision == 'curator_draft':
        proposal.provenance = 'curator'
    else:
        proposal.source_value = 'curated-summary'
        proposal.value_kind = 'string'
    proposal.save()
    before = FieldConceptMapping.objects.filter(pk=proposal.pk).values().get()
    repair()
    assert FieldConceptMapping.objects.filter(pk=proposal.pk).values().get() == before


def test_genomic_status_mapping_is_unchanged(proposal):
    concept = ConceptFactory(
        concept_code='69548-6', vocabulary=proposal.concept.vocabulary,
        domain=DomainFactory(domain_id='Measurement', domain_name='Measurement'),
    )
    status = FieldConceptMapping.objects.create(
        field_name='genetic_mutations.status', concept=concept,
        vocabulary_id='LOINC', concept_code='69548-6', omop_table='measurement',
        source_value='genomics:status', value_kind='string', status='approved',
    )
    before = FieldConceptMapping.objects.filter(pk=status.pk).values().get()
    repair()
    assert FieldConceptMapping.objects.filter(pk=status.pk).values().get() == before
