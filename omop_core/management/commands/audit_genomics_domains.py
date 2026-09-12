"""Check that genomics FieldConceptMapping.omop_table values match the
installed LOINC vocabulary's standard domain for each component.

Run after ``load_athena_vocabularies`` to catch domain drift between LOINC
releases and the seeded mappings.

    DATABASE_URL="..." python manage.py audit_genomics_domains

Exits 0 if all mappings match (or LOINC is not loaded).  Exits 1 if any
mapping's ``omop_table`` disagrees with the concept's domain.
"""
import sys

from django.core.management.base import BaseCommand

from omop_core.models import Concept, FieldConceptMapping


class Command(BaseCommand):
    help = 'Audit genomics component domain assignments against installed LOINC.'

    def handle(self, *args, **options):
        if not Concept.objects.filter(vocabulary_id='LOINC').exists():
            self.stdout.write('LOINC vocabulary not loaded — nothing to audit.')
            return

        mappings = FieldConceptMapping.objects.filter(
            field_name__startswith='genetic_mutations.',
            status='approved',
        ).select_related('concept')

        if not mappings.exists():
            self.stdout.write('No genomics component mappings found — run migrations first.')
            return

        mismatches = []
        resolved = 0
        skipped = 0

        for m in mappings:
            # Only audit LOINC-coded components.
            if not m.vocabulary_id or m.vocabulary_id != 'LOINC' or not m.concept_code:
                skipped += 1
                continue

            concept = Concept.objects.filter(
                vocabulary_id='LOINC',
                concept_code=m.concept_code,
                standard_concept='S',
                invalid_reason__isnull=True,
            ).first()

            if concept is None:
                self.stdout.write(
                    self.style.WARNING(
                        f'  {m.field_name}: LOINC {m.concept_code} not found in vocabulary'
                    )
                )
                continue

            resolved += 1
            expected_table = concept.domain_id.lower()

            if m.omop_table != expected_table:
                mismatches.append({
                    'field': m.field_name,
                    'code': m.concept_code,
                    'mapping_table': m.omop_table,
                    'loinc_domain': concept.domain_id,
                    'concept_on_mapping': m.concept_id,
                    'correct_concept': concept.pk,
                })

        self.stdout.write(
            f'Audited {resolved} LOINC-coded mappings, '
            f'{skipped} non-LOINC skipped.'
        )

        if not mismatches:
            self.stdout.write(self.style.SUCCESS('All domain assignments match.'))
            return

        self.stdout.write(
            self.style.ERROR(f'\n{len(mismatches)} domain mismatch(es):')
        )
        for m in mismatches:
            self.stdout.write(
                f"  {m['field']}: LOINC {m['code']} is {m['loinc_domain']}, "
                f"mapping says {m['mapping_table']}"
            )
            if m['concept_on_mapping'] == 0 and m['correct_concept'] != 0:
                self.stdout.write(
                    f"    → mapping has concept 0 but should be {m['correct_concept']}"
                )

        self.stdout.write(
            '\nTo fix: update the FieldConceptMapping rows via a migration or '
            'the admin, setting omop_table to match the LOINC domain and '
            'concept to the resolved standard concept.'
        )
        sys.exit(1)
