"""
Management command: populate_genomics_sample_data

Seeds plausible genetic variant data onto patients using save_variant() so that
OMOP Measurement/Observation rows, PatientRecord projections, and the
GenomicsTab all populate correctly.

Usage:
    DATABASE_URL="..." python manage.py populate_genomics_sample_data [--count 5] [--dry-run]
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from omop_core.models import Concept, FieldConceptMapping, PatientRecord
from omop_core.services.genomics import delete_variant, list_variants, save_variant
from omop_core.services.genomics_catalog import disease_code


# ── Variant pools by disease code ────────────────────────────────────────────

_HGVS_VARIANTS = {
    'brca1':  ['c.68_69delAG', 'c.5266dupC', 'c.181T>G'],
    'brca2':  ['c.5946delT', 'c.6174delT'],
    'pik3ca': ['c.3140A>G', 'c.1633G>A'],
    'tp53':   ['c.743G>A', 'c.818G>A'],
    'esr1':   ['c.1610A>G', 'c.1613A>G'],
    'palb1':  ['c.3113G>A', 'c.509_510delGA'],
    'kras':   ['c.35G>T', 'c.35G>A', 'c.34G>T'],
    'nras':   ['c.181C>A', 'c.182A>G'],
    'braf':   ['c.1799T>A'],
    'ccnd1':  ['c.870G>A', 'c.723G>A'],
    'notch1': ['c.7541_7542delCT', 'c.7544T>C'],
    'notch2': ['c.7189C>T', 'c.6898G>A'],
    'atm':    ['c.8545C>T', 'c.5557G>A'],
    'sf3b1':  ['c.2098A>G', 'c.1997A>G', 'c.1874G>A'],
    'bcl2':   ['c.455T>C'],
    'ezh2':   ['c.1936T>C', 'c.2044G>A'],
    'kmt2d':  ['c.8390delG', 'c.13882C>T'],
    'crebbp': ['c.4414A>G', 'c.4406T>G'],
}

_AMINO_ACID_CHANGES = {
    'brca1':  ['p.Glu23ValfsTer17', 'p.Gln1756ProfsTer74', 'p.Cys61Gly'],
    'brca2':  ['p.Ser1982ArgfsTer22', 'p.Ala2058GlyfsTer3'],
    'pik3ca': ['p.His1047Arg', 'p.Glu545Lys'],
    'tp53':   ['p.Arg248Gln', 'p.Arg273His'],
    'esr1':   ['p.Tyr537Ser', 'p.Asp538Gly'],
    'kras':   ['p.Gly12Val', 'p.Gly12Asp', 'p.Gly12Cys'],
    'nras':   ['p.Gln61Lys', 'p.Gln61Arg'],
    'braf':   ['p.Val600Glu'],
}

_DISEASE_POOLS = {
    'BC': [
        {'marker_key': 'brca1',  'gene': 'BRCA1',  'kind': 'gene', 'prevalence': 0.15},
        {'marker_key': 'brca2',  'gene': 'BRCA2',  'kind': 'gene', 'prevalence': 0.15},
        {'marker_key': 'pik3ca', 'gene': 'PIK3CA', 'kind': 'gene', 'prevalence': 0.35},
        {'marker_key': 'tp53',   'gene': 'TP53',   'kind': 'gene', 'prevalence': 0.30},
        {'marker_key': 'esr1',   'gene': 'ESR1',   'kind': 'gene', 'prevalence': 0.20},
        {'marker_key': 'palb1',  'gene': 'PALB1',  'kind': 'gene', 'prevalence': 0.08},
    ],
    'MM': [
        {'marker_key': 'kras',         'gene': 'KRAS',           'kind': 'gene',        'prevalence': 0.25},
        {'marker_key': 'nras',         'gene': 'NRAS',           'kind': 'gene',        'prevalence': 0.20},
        {'marker_key': 'braf',         'gene': 'BRAF',           'kind': 'gene',        'prevalence': 0.05},
        {'marker_key': 'tp53',         'gene': 'TP53',           'kind': 'gene',        'prevalence': 0.10},
        {'marker_key': 'del17p',       'gene': 'TP53',           'kind': 'abnormality', 'prevalence': 0.10},
        {'marker_key': 't414',         'gene': 'FGFR3/NSD2/IGH','kind': 'abnormality', 'prevalence': 0.15},
        {'marker_key': 't1114',        'gene': 'CCND1/IGH',     'kind': 'abnormality', 'prevalence': 0.20},
        {'marker_key': 't1416',        'gene': 'IGH/MAF',       'kind': 'abnormality', 'prevalence': 0.05},
        {'marker_key': 'gain1q',       'gene': '1q21',          'kind': 'abnormality', 'prevalence': 0.40},
        {'marker_key': 'hyperdiploidy','gene': 'Chromosomal',   'kind': 'abnormality', 'prevalence': 0.45},
    ],
    'FL': [
        {'marker_key': 'bcl2',   'gene': 'BCL2',   'kind': 'gene',        'prevalence': 0.85},
        {'marker_key': 'ezh2',   'gene': 'EZH2',   'kind': 'gene',        'prevalence': 0.25},
        {'marker_key': 'kmt2d',  'gene': 'KMT2D',  'kind': 'gene',        'prevalence': 0.70},
        {'marker_key': 'crebbp', 'gene': 'CREBBP',  'kind': 'gene',        'prevalence': 0.65},
        {'marker_key': 'bcl6',   'gene': 'BCL6',   'kind': 'abnormality', 'prevalence': 0.30},
    ],
    'MCL': [
        {'marker_key': 'ccnd1',             'gene': 'CCND1',       'kind': 'gene',        'prevalence': 0.30},
        {'marker_key': 'tp53',              'gene': 'TP53',        'kind': 'gene',        'prevalence': 0.15},
        {'marker_key': 'notch1',            'gene': 'NOTCH1',      'kind': 'gene',        'prevalence': 0.10},
        {'marker_key': 'notch2',            'gene': 'NOTCH2',      'kind': 'gene',        'prevalence': 0.08},
        {'marker_key': 'atm',              'gene': 'ATM',         'kind': 'gene',        'prevalence': 0.40},
        {'marker_key': 'del17p',           'gene': 'TP53',        'kind': 'abnormality', 'prevalence': 0.20},
        {'marker_key': 't1114',            'gene': 'CCND1/IGH',   'kind': 'abnormality', 'prevalence': 0.90},
        {'marker_key': 'complex_karyotype','gene': 'Chromosomal', 'kind': 'abnormality', 'prevalence': 0.25},
    ],
    'CLL': [
        {'marker_key': 'tp53',      'gene': 'TP53',  'kind': 'gene',        'prevalence': 0.10},
        {'marker_key': 'sf3b1',     'gene': 'SF3B1', 'kind': 'gene',        'prevalence': 0.15},
        {'marker_key': 'atm',       'gene': 'ATM',   'kind': 'gene',        'prevalence': 0.12},
        {'marker_key': 'notch1',    'gene': 'NOTCH1','kind': 'gene',        'prevalence': 0.12},
        {'marker_key': 'del17p',    'gene': 'TP53',  'kind': 'abnormality', 'prevalence': 0.10},
        {'marker_key': 'del11q',    'gene': '11q',   'kind': 'abnormality', 'prevalence': 0.18},
        {'marker_key': 'del13q',    'gene': '13q',   'kind': 'abnormality', 'prevalence': 0.55},
        {'marker_key': 'trisomy12', 'gene': '12',    'kind': 'abnormality', 'prevalence': 0.15},
    ],
}

# Abnormality label lookup (from the catalog).
_ABNORMALITY_LABELS = {
    'del17p': 'del(17p)', 't414': 't(4;14)', 't1114': 't(11;14)',
    't1416': 't(14;16)', 'gain1q': '1q21 gain / amplification',
    'hyperdiploidy': 'Hyperdiploidy', 'bcl6': 'BCL6 rearrangement',
    'complex_karyotype': 'Complex karyotype', 'del11q': 'del(11q)',
    'del13q': 'del(13q)', 'trisomy12': 'Trisomy 12',
}

_SLUG_MAP = {
    'BC': 'breast-cancer', 'MM': 'multiple-myeloma',
    'FL': 'follicular-lymphoma', 'MCL': 'mantle-cell-lymphoma',
    'CLL': 'chronic-lymphocytic-leukemia',
}
_SLUG_TO_CODE = {v: k for k, v in _SLUG_MAP.items()}

_INTERPRETATIONS = ['Pathogenic', 'Likely pathogenic', 'VUS', 'Likely benign', 'Benign']
_ORIGINS = ['Germline', 'Somatic']
_METHODS = ['NGS', 'Sanger sequencing', 'PCR']


def _random_test_date():
    """Random date within the last 2 years."""
    days_ago = random.randint(1, 730)
    return (date.today() - timedelta(days=days_ago)).isoformat()


def _build_gene_payload(entry):
    """Build a full clinical detail payload for a gene marker."""
    key = entry['marker_key']
    hgvs = _HGVS_VARIANTS.get(key)
    payload = {
        'gene': entry['gene'],
        'marker_key': key,
        'variant': random.choice(hgvs) if hgvs else '',
        'interpretation': random.choice(_INTERPRETATIONS),
        'origin': random.choice(_ORIGINS),
        'status': 'present',
        'test_date': _random_test_date(),
        'genome_assembly': 'GRCh38',
        'variant_analysis_method_type': random.choice(_METHODS),
    }
    aa = _AMINO_ACID_CHANGES.get(key)
    if aa:
        payload['amino_acid_change'] = random.choice(aa)
    if random.random() < 0.6:
        payload['allelic_frequency'] = Decimal(str(round(random.uniform(0.5, 85.0), 1)))
        payload['allelic_frequency_unit'] = '%'
    return payload


def _build_abnormality_payload(entry):
    """Build a status-only payload for an abnormality marker."""
    return {
        'gene': entry['gene'],
        'marker_key': entry['marker_key'],
        'variant_name': _ABNORMALITY_LABELS.get(entry['marker_key'], entry['marker_key']),
        'status': random.choice(['present', 'absent']),
        'test_date': _random_test_date(),
    }


def _select_markers(pool, min_count=1, max_count=6):
    """Select markers by prevalence, guaranteeing at least min_count."""
    selected = [entry for entry in pool if random.random() < entry['prevalence']]
    if len(selected) < min_count:
        remaining = [e for e in pool if e not in selected]
        random.shuffle(remaining)
        selected.extend(remaining[:min_count - len(selected)])
    return selected[:max_count]


class Command(BaseCommand):
    help = 'Seed plausible genomic variant data onto patients'

    def add_arguments(self, parser):
        parser.add_argument('--org', type=str, help='Filter patients by organization slug')
        parser.add_argument('--count', type=int, help='Seed exactly N patients (default: 10%% of eligible)')
        parser.add_argument('--patient', type=str, help='Seed a single patient (person_id or email)')
        parser.add_argument('--disease', type=str, help='Filter by disease code (BC, MM, FL, MCL, CLL)')
        parser.add_argument('--all', action='store_true', help='Seed all eligible patients')
        parser.add_argument('--overwrite', action='store_true', help='Delete existing variants before re-seeding')
        parser.add_argument('--dry-run', action='store_true', help='Preview what would be seeded, no writes')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        overwrite = options['overwrite']

        # Precondition: required OMOP concepts and genomics field mappings must exist.
        if not dry_run:
            missing = []
            if not Concept.objects.filter(pk=0).exists():
                missing.append('Concept(pk=0)')
            if not Concept.objects.filter(pk=32817).exists():
                missing.append('Concept(pk=32817)')
            if missing:
                raise CommandError(f'Required OMOP concepts missing: {", ".join(missing)}. Load vocabularies first.')
            genomics_mappings = FieldConceptMapping.objects.filter(
                field_name__startswith='genomics_', status='approved',
            ).count()
            if genomics_mappings == 0:
                raise CommandError(
                    'No approved genomics FieldConceptMapping rows found. '
                    'Run migrations (0224_seed_genomics_mappings) first.'
                )

        # Build queryset.
        qs = PatientRecord.objects.select_related('person').exclude(
            disease_slug__isnull=True,
        ).exclude(disease_slug='')

        if options['org']:
            qs = qs.filter(organization__slug=options['org'])

        if options['disease']:
            code = disease_code(options['disease'])
            if code is None:
                raise CommandError(f'Unknown disease code: {options["disease"]}')
            qs = qs.filter(disease_slug=_SLUG_MAP[code])

        if options['patient']:
            val = options['patient']
            try:
                pid = int(val)
                qs = qs.filter(person_id=pid)
            except ValueError:
                qs = qs.filter(email=val)

        # Filter to patients whose disease_slug maps to a known pool.
        qs = qs.filter(disease_slug__in=_SLUG_MAP.values())

        if not overwrite:
            qs = qs.filter(genetic_mutations=[])

        qs = qs.order_by('person_id')

        total_eligible = qs.count()
        if total_eligible == 0:
            if options['patient']:
                self._diagnose_patient(options['patient'], overwrite)
            self.stdout.write('No eligible patients found.')
            return

        # Determine count.
        if options['patient']:
            count = total_eligible
        elif options['all']:
            count = total_eligible
        elif options['count'] is not None:
            count = min(options['count'], total_eligible)
        else:
            count = max(1, total_eligible // 10)

        patients = list(qs[:count])
        self.stdout.write(f'Seeding {len(patients)} of {total_eligible} eligible patients'
                          f'{" (dry run)" if dry_run else ""}')

        seeded = 0
        total_variants = 0
        for pr in patients:
            code = _SLUG_TO_CODE.get(pr.disease_slug)
            if code is None:
                continue
            pool = _DISEASE_POOLS.get(code)
            if not pool:
                continue

            markers = _select_markers(pool)
            if dry_run:
                marker_names = ', '.join(m['marker_key'] for m in markers)
                self.stdout.write(f'  [DRY RUN] person_id={pr.person_id} ({code}): '
                                  f'{len(markers)} variants — {marker_names}')
                seeded += 1
                total_variants += len(markers)
                continue

            try:
                with transaction.atomic():
                    if overwrite:
                        existing = list_variants(pr.person)
                        for v in existing:
                            delete_variant(pr.person, v['id'])

                    for entry in markers:
                        if entry['kind'] == 'gene':
                            payload = _build_gene_payload(entry)
                        else:
                            payload = _build_abnormality_payload(entry)
                        save_variant(pr.person, payload)
                        total_variants += 1
            except Exception as e:
                self.stderr.write(f'  ERROR person_id={pr.person_id}: {e}')
                continue

            seeded += 1
            self.stdout.write(f'  person_id={pr.person_id} ({code}): {len(markers)} variants')

        self.stdout.write(self.style.SUCCESS(
            f'Done. Seeded {total_variants} variants across {seeded} patients.'
        ))

    def _diagnose_patient(self, val, overwrite):
        """Provide a specific error when --patient targets an ineligible patient."""
        try:
            pid = int(val)
            pr = PatientRecord.objects.filter(person_id=pid).first()
        except ValueError:
            pr = PatientRecord.objects.filter(email=val).first()
        if pr is None:
            raise CommandError(f'Patient not found: {val}')
        if not pr.disease_slug:
            raise CommandError(f'Patient {val} has no disease_slug set.')
        if pr.disease_slug not in _SLUG_MAP.values():
            raise CommandError(f'Patient {val} has unsupported disease: {pr.disease_slug}')
        if not overwrite and pr.genetic_mutations:
            raise CommandError(f'Patient {val} already has variants. Use --overwrite to replace.')
