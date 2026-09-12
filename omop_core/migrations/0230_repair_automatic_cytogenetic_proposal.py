"""Replace the unreviewed legacy panel proposal with the summary recipe."""

from django.db import migrations
from django.utils import timezone


def repair_automatic_proposal(apps, schema_editor):
    using = schema_editor.connection.alias if schema_editor else 'default'
    Concept = apps.get_model('omop_core', 'Concept')
    Mapping = apps.get_model('omop_core', 'FieldConceptMapping')
    if not Concept.objects.using(using).filter(pk=0).exists():
        return

    # This exact legacy auto-proposal exists on staging. It predates recorded
    # provenance and was preserved by the rename's get_or_create. Restrict the
    # repair to its untouched recipe: never replace reviewed, curator-authored,
    # rejected, or otherwise customized mappings.
    Mapping.objects.using(using).filter(
        field_name='cytogenetic_markers', status='proposed', provenance='',
        notes='Auto-proposed from field suggestion.',
        reviewer_id__isnull=True, reviewed_at__isnull=True,
        vocabulary_id='LOINC', concept_code='55232-3',
        concept__vocabulary_id='LOINC', concept__concept_code='55232-3',
        omop_table__iexact='observation', source_value='', value_kind='',
        value_vocabulary='', unit='', type_concept_id__isnull=True, multiple=False,
    ).update(
        concept_id=0, vocabulary_id='', concept_code='',
        omop_table='observation', source_value='mm-cytogenetic-markers',
        value_kind='string', multiple=True, status='approved',
        provenance='system_generated', updated_at=timezone.now(),
        notes=(
            'Canonical cytogenetic marker summary; no verified standard equivalent. '
            'OMOP concept 0 with local source mm-cytogenetic-markers. '
            'Replaces the unreviewed automatic LOINC 55232-3 panel proposal.'
        ),
    )


class Migration(migrations.Migration):
    dependencies = [('omop_core', '0229_merge_cytogenetics_and_domain_audit')]
    operations = [
        migrations.RunPython(repair_automatic_proposal, migrations.RunPython.noop),
    ]
