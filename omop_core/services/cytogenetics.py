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
LEGACY_CONCEPT_CODE = '107675007'  # Chromosomal morphology, for imported free text.
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
        vocabulary_id__in={'SNOMED'} | {c.vocabulary_id for _, c in preferred if c},
        concept_code__in={LEGACY_CONCEPT_CODE} | {c.code for _, c in preferred if c},
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
        entry['projection'] = {
            'omop_table': 'observation', 'choice_projections': recipes,
            'choice_values': [choice.display for choice in choices],
        }
        legacy_concept = concepts.get(('SNOMED', LEGACY_CONCEPT_CODE))
        if legacy_concept:
            entry['projection']['legacy_projection'] = {
                'omop_table': 'observation', 'concept_id': legacy_concept.pk,
                'source_value': LEGACY_SOURCE, 'type_concept_id': 32817,
                'value_kind': 'string',
            }
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
    # An unavailable mapping for a curated selection must still fail atomically.
    # Unlisted historical text is preserved by the aggregate recipe instead.
    choice_values = set(projection.get('choice_values', recipes))
    if any(marker in choice_values and marker not in recipes for marker in selected):
        return False
    with transaction.atomic():
        Person.objects.select_for_update().get(pk=person.pk)
        rows = list(Observation.objects.filter(person=person, is_erroneous=False).filter(
            Q(observation_source_value__startswith=SOURCE_PREFIX)
            | Q(observation_source_value=LEGACY_SOURCE)))
        previous = values_from_rows(rows)
        removed = set(previous) - set(selected)
        today = timezone.localdate()
        after_pk = max((row.pk for row in rows if row.observation_date == today
                        and row.observation_source_value == LEGACY_SOURCE), default=None)
        legacy_selected = [marker for marker in selected if marker not in recipes]
        if legacy_selected or any(marker not in recipes for marker in removed):
            legacy_recipe = projection.get('legacy_projection')
            if not legacy_recipe:
                return False
            # Replace the legacy set before reasserting the selected coded
            # markers. This also clears removed unlisted values without needing
            # to invent an individual concept mapping for them. The new row
            # must sort after every same-day row it supersedes.
            boundary = max((row.pk for row in rows if row.observation_date == today), default=None)
            if not project_single_value(person, FIELD, ', '.join(legacy_selected) or None,
                                        legacy_recipe, acknowledge_existing=True, after_pk=boundary):
                raise ValueError('Cytogenetic legacy projection failed')
            after_pk = Observation.objects.filter(
                person=person, is_erroneous=False, observation_date=today,
                observation_source_value=LEGACY_SOURCE,
            ).order_by('-observation_id').values_list('pk', flat=True).first()
            removed = set()  # The replacement aggregate clears the previous set.
        # All selected markers get today's affirmative row. Removed markers get
        # a dated clear; earlier rows remain intact as history.
        for marker in [m for m in selected if m in recipes] + sorted(removed):
            if not project_single_value(person, FIELD, marker if marker in selected else None,
                                        recipes[marker], acknowledge_existing=True, after_pk=after_pk):
                raise ValueError('Cytogenetic projection failed')
    return True
