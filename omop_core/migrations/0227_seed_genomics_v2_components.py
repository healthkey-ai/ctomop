"""Seed new genomic component recipes: clone_fraction, transcript_dna_change,
coverage_depth and amino_acid_change_type.

None of the LOINCs (82121-5, 48004-6, 48006-1) resolve in the installed
vocabulary, so all use genomics: source keys with concept 0.
"""
from django.db import migrations
from django.utils import timezone

_RECIPES = [
    # (field_name, source_value, omop_table, value_kind, unit, notes)
    (
        'genetic_mutations.clone_fraction',
        'genomics:clone_fraction',
        'measurement',
        'number',
        '%',
        'FISH clone fraction (percent of nuclei). Not allelic_frequency.',
    ),
    (
        'genetic_mutations.transcript_dna_change',
        'genomics:transcript_dna_change',
        'measurement',
        'string',
        '',
        'Transcript DNA change (c.HGVS, LOINC 48004-6). '
        'Distinct from genomic_dna_change (81290-9).',
    ),
    (
        'genetic_mutations.coverage_depth',
        'genomics:coverage_depth',
        'measurement',
        'number',
        '',
        'Coverage depth (LOINC 82121-5). Per-variant only.',
    ),
    (
        'genetic_mutations.amino_acid_change_type',
        'genomics:amino_acid_change_type',
        'measurement',
        'string',
        '',
        'Amino acid change type (LOINC 48006-1, e.g. missense). '
        'Distinct from amino_acid_change (48005-3).',
    ),
]


def seed_v2_components(apps, schema_editor):
    using = schema_editor.connection.alias
    Concept = apps.get_model('omop_core', 'Concept')
    Mapping = apps.get_model('omop_core', 'FieldConceptMapping')
    zero = Concept.objects.using(using).filter(pk=0).first()
    for field_name, source_value, omop_table, value_kind, unit, notes in _RECIPES:
        Mapping.objects.using(using).get_or_create(
            field_name=field_name,
            defaults={
                'concept': zero,
                'vocabulary_id': '',
                'concept_code': '',
                'source_value': source_value,
                'omop_table': omop_table,
                'value_kind': value_kind,
                'unit': unit,
                'type_concept_id': 32817,
                'multiple': False,
                'status': 'approved',
                'reviewed_at': timezone.now(),
                'notes': notes,
            },
        )


class Migration(migrations.Migration):
    dependencies = [('omop_core', '0226_seed_genomics_status_component')]
    operations = [migrations.RunPython(seed_v2_components, migrations.RunPython.noop)]
