"""Versioned CancerBot priority catalog; no patient facts are created by reads."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def catalog():
    return json.loads((Path(__file__).resolve().parent.parent / 'data/genomics_catalog_v1.json').read_text())


def markers():
    return catalog()['markers']


def patient_fields():
    return {m['field_name']: m for m in markers()}


def disease_code(value):
    key = str(value or '').strip().lower().replace('_', ' ').replace('-', ' ')
    aliases = {
        'bc': 'BC', 'breast': 'BC', 'breast cancer': 'BC',
        'mm': 'MM', 'myeloma': 'MM', 'multiple myeloma': 'MM',
        'fl': 'FL', 'lymphoma': 'FL', 'follicular lymphoma': 'FL',
        'mcl': 'MCL', 'mantle cell lymphoma': 'MCL',
        'cll': 'CLL', 'chronic lymphocytic leukemia': 'CLL',
        'chronic lymphocytic leukaemia': 'CLL',
    }
    return aliases.get(key)


def marker_for_variant(variant):
    assigned = variant.get('marker_key')
    if assigned:
        return next((m for m in markers() if m['key'] == assigned), None)
    gene = (variant.get('gene') or '').upper()
    names = {str(variant.get(k) or '').lower().replace(' ', '') for k in ('variant', 'variant_name')}
    # Exact known abnormalities take precedence; do not infer a deletion from
    # a TP53 mutation, or split combined NOTCH/ATM source statements.
    for m in markers():
        if names & {a.lower().replace(' ', '') for a in [*m['aliases'], m['label']] if a} and m['kind'] == 'abnormality':
            return m
    return next((m for m in markers() if m['gene'].upper() == gene and m['kind'] == 'gene'), None)


# Markers that can be either asserted (from a report) or derived (computed
# at projection time from other stored findings).
_DERIVABLE_MARKERS = frozenset({'complex_karyotype', 'complex_karyotype_excl_t1114'})


def _derive_complex_karyotype(variants):
    """Stub: complex karyotype threshold logic is an open clinical question.

    Returns None — the derived path is not yet implemented.
    """
    return None


def _derive_complex_karyotype_excl_t1114(variants):
    """Stub: same as _derive_complex_karyotype, excluding t(11;14).

    Returns None — the derived path is not yet implemented.
    """
    return None


_DERIVATION_FUNCTIONS = {
    'complex_karyotype': _derive_complex_karyotype,
    'complex_karyotype_excl_t1114': _derive_complex_karyotype_excl_t1114,
}


def project_priority_variants(variants):
    result = {name: [] for name in patient_fields()}
    for variant in variants:
        marker = marker_for_variant(variant)
        if marker:
            entry = dict(variant)
            if marker['key'] in _DERIVABLE_MARKERS:
                entry['provenance'] = 'asserted'
            result[marker['field_name']].append(entry)
    # For derivable markers with no asserted finding, attempt derivation.
    for marker_key in _DERIVABLE_MARKERS:
        field = next(m['field_name'] for m in markers() if m['key'] == marker_key)
        if not result[field]:
            derived = _DERIVATION_FUNCTIONS[marker_key](variants)
            if derived is not None:
                derived['provenance'] = 'derived'
                result[field].append(derived)
    return result
