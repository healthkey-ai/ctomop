# Cytogenetic marker selections (#1049)

The Disease tab's **Cytogenetic Markers** control is a multiselect. The canonical
PatientRecord/API key is `cytogenetic_markers`; writes also accept the historical
`cytogenic_markers` spelling for compatibility. Clients
can PATCH a list or comma-separated text. The server normalizes legacy spellings
such as `del(17p13)`, `1q21 amplification`, and `t(4,14)` to the existing matching
tokens (`del17p`, `1q_amp`, and `t(4;14)`) before saving.

Each selection creates its own Observation through the PatientRecord-first save
path. `FieldChoiceCode` holds the per-value mapping; the writable descriptor
exposes the code, vocabulary, resolved concept ID and concept name for every
option. The field-level approved `FieldConceptMapping` enables this recipe.

| Selected field value | Standard SNOMED code | OMOP concept ID | Standard Observation category |
| --- | --- | --- | --- |
| del17p | 67285006 | 4284835 | Deletion of short arm |
| t(4;14) | 15897004 | 4049480 | Chromosomal translocation |
| t(11;14) | 15897004 | 4049480 | Chromosomal translocation |
| t(14;16) | 15897004 | 4049480 | Chromosomal translocation |
| 1q_gain | 41669009 | 4215516 | Alteration of chromosome structure |
| 1q_amp | 41669009 | 4215516 | Alteration of chromosome structure |
| hyperdiploidy | 55597007 | 4208087 | Hyperploidy |
| del13q | 64329008 | 4275261 | Deletion of long arm |
| MYC rearrangement | 41669009 | 4215516 | Alteration of chromosome structure |

These category mappings are **broader than the individual markers**. Exact marker
identity is retained in `value_as_string` and the distinct
`observation_source_value = 'cytogenetic:' + selected_value`. Consumers must use
that identity when matching an individual abnormality; the category concept
alone does not distinguish translocations, gain/amplification, or affected loci.
Hyperdiploidy is a synonym of the mapped Hyperploidy concept.

IDs, codes, standard status and Observation domains were checked against the
Athena vocabulary export (SNOMED International 2025-02-01 / US 2025-03-01 / UK
2025-04-09). The migration seeds only these real Athena concepts plus the
field-level Chromosomal morphology concept (SNOMED 107675007 / OMOP 4030018).
Runtime resolution additionally requires an active, valid-date, standard concept
in the Observation domain. Marker-specific LOINC tests belong to Measurement and
are not substituted into Observation's standard concept column.

For example, selecting `t(4;14)` and `t(11;14)` produces two Observation rows with
concept 4049480, distinct source keys, and the corresponding marker strings.
Repeated saves reuse today's rows. If a same-day aggregate import superseded
those rows, corrections create newer rows so the import cannot undo the edit.
Deselecting a marker records a dated clear;
earlier results remain as history. Full OMOP refreshes read these rows and legacy
`mm-cytogenetic-markers` aggregate imports, including clears, without resurrecting
removed selections. Newer individual imported marker observations update the
matching PatientRecord values.

Projection is atomic across the selection. If a selected concept is unavailable
or a row fails, the PatientRecord edit remains pending and protected from stale
OMOP refreshes. Unrecognized new values are rejected; existing unrecognized
legacy text is preserved without claiming it has an individual concept mapping.
When edits retain or remove unlisted legacy values, a dated Chromosomal
morphology aggregate replaces the legacy set, followed by a separate coded row
for each selected supported marker. This lets legacy text be retained or cleared
without blocking supported selections. The aggregate and individual rows are
written in one transaction.

Legacy aggregate NOTE references remain readable with the existing patient/fact
ownership checks. Long retained legacy text still uses that lossless storage.
Existing scalar curator recipes remain supported; migration 0230 enables the
per-value standard Observation recipe after the canonical field rename.
