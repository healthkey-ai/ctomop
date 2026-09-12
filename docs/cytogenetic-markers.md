# Cytogenetic marker selections (#1049)

The Disease tab's **Cytogenetic Markers** control is a multiselect. The existing
`cytogenic_markers` PatientRecord/API key is retained for compatibility. Clients
can PATCH a list or comma-separated text. The server normalizes legacy spellings
such as `del17p`, `1q_amp`, and `t(4,14)` before saving.

Each selection creates its own Observation through the PatientRecord-first save
path. `FieldChoiceCode` holds the per-value mapping; the writable descriptor
exposes the code, vocabulary, resolved concept ID and concept name for every
option. The field-level approved `FieldConceptMapping` enables this recipe.

| Selected field value | Standard SNOMED code | OMOP concept ID | Standard Observation category |
| --- | --- | --- | --- |
| del(17p13) | 67285006 | 4284835 | Deletion of short arm |
| t(4;14) | 15897004 | 4049480 | Chromosomal translocation |
| t(11;14) | 15897004 | 4049480 | Chromosomal translocation |
| t(14;16) | 15897004 | 4049480 | Chromosomal translocation |
| 1q21 gain | 41669009 | 4215516 | Alteration of chromosome structure |
| 1q21 amplification | 41669009 | 4215516 | Alteration of chromosome structure |
| hyperdiploidy | 55597007 | 4208087 | Hyperploidy |
| del(13q) | 64329008 | 4275261 | Deletion of long arm |
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
Repeated saves reuse today's rows. Deselecting a marker records a dated clear;
earlier results remain as history. Full OMOP refreshes read these rows and legacy
`mm-cytogenetic-markers` aggregate imports, including clears, without resurrecting
removed selections. Newer individual imported marker observations update the
matching PatientRecord values.

Projection is atomic across the selection. If a selected concept is unavailable
or a row fails, the PatientRecord edit remains pending and protected from stale
OMOP refreshes. Unrecognized new values are rejected; existing unrecognized
legacy text is preserved without claiming it has an approved concept mapping.
