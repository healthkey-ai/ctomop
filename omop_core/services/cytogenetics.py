"""Canonical multiple-myeloma cytogenetic marker values."""

import re

CANONICAL_CYTOGENETIC_MARKERS = (
    'del17p',
    't(4;14)',
    't(11;14)',
    't(14;16)',
    '1q_gain',
    '1q_amp',
    'hyperdiploidy',
    'del13q',
    'MYC rearrangement',
)

_ALIASES = {
    'del(17p13)': 'del17p',
    'del(17p)': 'del17p',
    'tp53/17p deletion': 'del17p',
    '1q21 amplification': '1q_amp',
    '1q21 gain': '1q_gain',
    '1q21 gain/amplification': '1q_gain',
    'fgfr3/igh translocation t(4;14)': 't(4;14)',
    'maf/igh translocation t(14;16)': 't(14;16)',
    'myc rearrangement': 'MYC rearrangement',
}
_CANONICAL_BY_CASEFOLD = {
    marker.casefold(): marker for marker in CANONICAL_CYTOGENETIC_MARKERS
}
_NO_MARKER_VALUES = {
    'standard risk — no high-risk markers detected',
    'standard risk - no high-risk markers detected',
}


def normalise_cytogenetic_markers(value, *, strict=False) -> str:
    """Return a stable, de-duplicated comma-separated marker list.

    UI writes use ``strict=True`` so PatientRecord never receives an answer the
    chooser cannot represent. Import refreshes are deliberately lossless:
    recognized aliases are normalized while unfamiliar source values survive.
    """
    if value in (None, ''):
        return ''
    parts = value if isinstance(value, (list, tuple)) else str(value).split(',')
    normalized = []
    unknown = []
    for part in parts:
        raw = str(part).strip()
        if not raw or raw.casefold() in _NO_MARKER_VALUES:
            continue
        folded = raw.casefold()
        marker = _ALIASES.get(folded) or _CANONICAL_BY_CASEFOLD.get(folded)
        if marker is None:
            unknown.append(raw)
            marker = raw
        if marker not in normalized:
            normalized.append(marker)
    if strict and unknown:
        raise ValueError(f"Unrecognized cytogenetic marker values: {unknown}")
    return ', '.join(normalized)


def _note_source(row):
    # Include the table: Measurement and Observation IDs can overlap.
    return f'cytogenetics:{row._meta.db_table}:{row.pk}'


def store_cytogenetic_summary(row, value):
    """Return (CDM-width text, note_changed), inside the projector transaction.

    Large selections live in a NOTE tied to this patient and this dated fact.
    The fact holds only a reference, so even a 19-digit NOTE ID fits in 60 chars.
    Same-day edits reuse the note; previous days keep their own full text.
    """
    from omop_core.models import Note
    from omop_core.services.pk import next_pk

    if len(value) <= row._meta.get_field('value_as_string').max_length:
        return value, False
    note = Note.objects.filter(
        person_id=row.person_id, note_source_value=_note_source(row),
    ).order_by('-note_id').first()
    changed = note is None or note.note_text != value
    if note is None:
        note = Note.objects.create(
            note_id=next_pk(Note, 'note_id'), person_id=row.person_id,
            note_date=getattr(row, f'{row._meta.db_table}_date'),
            note_type_concept_id=0, note_source_value=_note_source(row),
            note_text=value,
        )
    elif changed:
        note.note_text = value
        note.save(update_fields=['note_text'])
    return f'[note:{note.pk}]', changed


def read_cytogenetic_summary(row):
    """Read full text only from a NOTE belonging to this patient and fact."""
    from omop_core.models import Note

    value = row.value_as_string
    match = re.fullmatch(r'\[note:(\d+)\]', value or '')
    if not match:
        return value
    # Both the built-in and curated extractors visit the same snapshot row.
    if not hasattr(row, '_cytogenetic_summary_text'):
        text = Note.objects.filter(
            pk=int(match.group(1)), person_id=row.person_id,
            note_source_value=_note_source(row),
        ).values_list('note_text', flat=True).first()
        row._cytogenetic_summary_text = text if text is not None else value
    return row._cytogenetic_summary_text
