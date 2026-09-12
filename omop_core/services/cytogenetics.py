"""Cytogenetic selections and their per-value standard Observation recipes.

SNOMED categories are broader than the named markers: preserve the exact marker
in value_as_string and a distinct source key. See docs/cytogenetic-markers.md.
"""
import re

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

FIELD = 'cytogenic_markers'  # Retain the existing database/API spelling.
SOURCE_PREFIX = 'cytogenetic:'
LEGACY_SOURCE = 'mm-cytogenetic-markers'
VALUES = (
    'del(17p13)', 't(4;14)', 't(11;14)', 't(14;16)', '1q21 gain',
    '1q21 amplification', 'hyperdiploidy', 'del(13q)', 'MYC rearrangement',
)
ALIASES = {
    'del17p': 'del(17p13)', 'del(17p)': 'del(17p13)',
    '1q_gain': '1q21 gain', '1q_amp': '1q21 amplification',
    'del13q': 'del(13q)',
    **{value.lower(): value for value in VALUES},
}


def selections(value):
    if value in (None, ''):
        return []
    if isinstance(value, str):
        # Legacy FHIR values can use t(4,14); commas inside parentheses are
        # part of the marker, not separators between selected markers.
        value = re.split(r',\s*(?![^()]*\))', value)
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError('Select cytogenetic markers as a list or comma-separated text.')
    result = []
    for item in value:
        item = item.strip()
        if item.startswith('t('):
            item = item.replace(',', ';')
        item = ALIASES.get(item.lower(), item)
        if item and item not in result:
            result.append(item)
    return result


def descriptor():
    from omop_core.models import Concept, FieldChoice, FieldConceptMapping

    entry = {'kind': 'direct', 'writable': True, 'target': 'patient_record',
             'value_kind': 'string', 'multiple': True}
    choices = list(FieldChoice.objects.filter(field_name=FIELD).prefetch_related('codes'))
    preferred = [(choice, next((c for c in choice.codes.all() if c.is_primary), None))
                 for choice in choices]
    concepts = {(c.vocabulary_id, c.concept_code): c for c in Concept.objects.filter(
        vocabulary_id__in={c.vocabulary_id for _, c in preferred if c},
        concept_code__in={c.code for _, c in preferred if c},
        standard_concept='S', domain_id='Observation', invalid_reason__isnull=True,
        valid_start_date__lte=timezone.localdate(), valid_end_date__gte=timezone.localdate(),
    )}
    options, recipes = [], {}
    for choice, code in preferred:
        concept = concepts.get((code.vocabulary_id, code.code)) if code else None
        option = {'value': choice.display, 'code': code.code if code else None,
                  'vocabulary': code.vocabulary_id if code else None,
                  'concept_id': concept.pk if concept else None,
                  'display': concept.concept_name if concept else None}
        options.append(option)
        if concept:
            recipes[choice.display] = {
                'omop_table': 'observation', 'concept_id': concept.pk,
                'source_value': SOURCE_PREFIX + choice.display,
                'type_concept_id': 32817, 'value_kind': 'string',
            }
    entry['options'] = options
    if FieldConceptMapping.objects.filter(field_name=FIELD, status='approved', multiple=True).exists():
        entry['projection'] = {'omop_table': 'observation', 'choice_projections': recipes}
    return entry


def values_from_rows(rows):
    """Merge dated marker observations with legacy aggregate imports, including clears."""
    from omop_core.services.omop_projection import CLEAR_VALUE

    current = {}
    for row in sorted(rows, key=lambda r: (r.observation_date, r.observation_id), reverse=True):
        source = row.observation_source_value or ''
        if source == LEGACY_SOURCE:
            legacy = selections(row.value_as_string)
            for marker in VALUES:
                current.setdefault(marker, marker in legacy)
            for marker in legacy:
                current.setdefault(marker, True)
            break
        if source.startswith(SOURCE_PREFIX):
            marker = source[len(SOURCE_PREFIX):]
            current.setdefault(marker, row.value_source_value != CLEAR_VALUE and bool(row.value_as_string))
    return [marker for marker in VALUES if current.get(marker)] + sorted(
        marker for marker, present in current.items() if present and marker not in VALUES)


def project_selections(person, value, projection):
    from omop_core.models import Observation, Person
    from omop_core.services.omop_projection import project_single_value

    selected = selections(value)
    recipes = projection['choice_projections']
    if any(marker not in recipes for marker in selected):
        return False
    with transaction.atomic():
        Person.objects.select_for_update().get(pk=person.pk)
        rows = list(Observation.objects.filter(person=person, is_erroneous=False).filter(
            Q(observation_source_value__startswith=SOURCE_PREFIX)
            | Q(observation_source_value=LEGACY_SOURCE)))
        previous = values_from_rows(rows)
        removed = set(previous) - set(selected)
        if any(marker not in recipes for marker in removed):
            return False
        # All selected markers get today's affirmative row. Removed markers get
        # a dated clear; earlier rows remain intact as history.
        for marker in list(selected) + sorted(removed):
            if not project_single_value(person, FIELD, marker if marker in selected else None,
                                        recipes[marker], acknowledge_existing=True):
                raise ValueError('Cytogenetic projection failed')
    return True
