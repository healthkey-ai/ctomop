# Genomics: as-implemented architecture

Implementation date: 2026-09-11. Covers the initial Genomics CRUD work and the
disease-priority mappings. The original implementation plan is preserved in
commit `2bf7a70`. Tracking: [#1179](https://github.com/healthkey-ai/promop/issues/1179),
[#1180](https://github.com/healthkey-ai/promop/issues/1180),
[#1181](https://github.com/healthkey-ai/promop/issues/1181).

## Delivery plan and scope

1. Include the initial Genomics CRUD implementation: linked OMOP facts, lossless
   text, validation, patient authorization, and the existing standalone/federated tab.
2. Freeze a disease/marker catalog from CancerBot commit
   `a840f8d9af2c35477e2b6b76f981b29f02c21eec`. Source files:
   `trials/services/value_options.py:558`, `markers_mapper.py`,
   `loaders/load_genetic_mutations.py`, `mutations_mapper.py`, and
   `patient_info/patient_info_attributes.py:65`.
3. Add named, list-valued PatientRecord projections for priority genes/abnormalities.
   Seed approved FieldConceptMappings and a disease catalog using a versioned
   fixture, migration and idempotent management command. Every edit uses these
   mappings to write canonical OMOP parents and linked attribute facts atomically.
4. Precreate presentation rows for the selected disease, without inserting clinical
   facts for missing results. Keep arbitrary variants and repeated findings. A
   disease change changes suggested rows, not the stored patient's findings.
5. Show Gene, Mutation, Origin and Interpretation; clicking a row opens an accessible
   dialog containing all original attributes plus assessment and provenance details.
   Remove genetic/molecular mutation editors from disease-specific tabs.
6. Test both directions (PatientRecord edits → OMOP and OMOP → PatientRecord),
   approval enforcement, migration/fixture idempotency, repeated findings, clears,
   access control, placeholders, disease switches and dialog CRUD on an isolated DB.
7. Review the complete diff, create a PR to dev, pass CI and merge. The sections
   below describe the resulting architecture and distinguish follow-up work.

## Decisions to preserve during implementation

- Empty, absent and untested are different states. Empty catalog rows are never
  interpreted as a negative test or counted as findings.
- Gene mutations and structural/cytogenetic findings need distinct catalog keys.
- CancerBot shares a union of hematologic options despite disease-specific comments;
  use the explicit per-disease descriptions and MCL criteria, not that union.
- Preserve source strings and uncertain legacy naming (including PALB1 and combined
  ATM/ATR or NOTCH1/NOTCH2) without silently inventing a molecular interpretation.
- Seeded approval authorizes the storage mapping, not expert validation of every
  example mutation or a patient's clinical interpretation.

## User experience and field ownership

Standalone and federated patient views share `GenomicsTab`. The second tab keeps
disease selection and disease-specific staging/clinical fields, but no mutation
editor. Removed controls include BC mutations, MCL molecular markers, MM cytogenetic
abnormalities and CLL/MCL TP53 disruption. Cytogenetic risk classification and
protein-expression biomarkers remain separate from variant editing.

The Genomics list shows Gene, Mutation, Origin, Interpretation. Clicking a row or
using Enter/Space opens a dialog with every attribute. Add/Edit use Save/Cancel;
Delete requires confirmation. Arbitrary genes and repeated findings are supported.
Changing disease changes only presentation priorities, never stored findings.
Deleting a finding restores its empty priority row. Empty rows create no OMOP facts.

## Catalog and named PatientRecord projections

`omop_core/data/genomics_catalog_v1.json` is a frozen fixture with 42 distinct
markers and 26 component recipes. It is not a runtime CancerBot dependency.
Every key below has a real JSON list field `genomics_<key>`, containing full
findings and stable parent IDs. `genetic_mutations` contains the general list.

| Disease | Priority keys (prefix with `genomics_` for the PatientRecord field) |
|---|---|
| BC | brca1, brca2, pik3ca, tp53, esr1, palb1 |
| MM | tp53, kras, nras, braf, myc, fam46c, dis3, xbp1, del17p, t414, t1114, t1416, gain1q, hyperdiploidy, chromothripsis, igh |
| FL | bcl2, ezh2, kmt2d, crebbp, bcl6 |
| MCL | tp53, myc, kmt2d, notch1, notch2, nsd2, cdkn2a, smarca4, ccnd1, del17p, t1114, bcl2_amplification, complex_karyotype, complex_karyotype_excl_t1114, atm_atr, notch1_notch2 |
| CLL | tp53, notch1, sf3b1, atm, del17p, del11q, del13q, trisomy12 |

Exact structural aliases are matched before generic genes. A TP53 mutation does
not imply del(17p). Combined ATM/ATR or NOTCH1/NOTCH2 statements are not split into
unsupported assertions. Legacy PALB1 remains flagged pending source-aware migration;
example mutations are not auto-selected or clinically validated by this feature.
CancerBot concerns assigned to `SamarElkassas`:
[PALB naming #4812](https://github.com/cancerbot-org/cancerbot/issues/4812),
[examples #5297](https://github.com/cancerbot-org/cancerbot/issues/5297),
[disease subsets #5298](https://github.com/cancerbot-org/cancerbot/issues/5298).

## Canonical storage and write-through

```text
Genomics dialog / named PatientRecord PATCH
  → patient authorization + approved mappings + validation
  → transaction / PatientRecord lock
      → one parent Measurement per finding
      → linked attribute Measurements / Observations
  → PatientRecord refresh
      → genetic_mutations + genomics_<marker> lists
  → list plus non-persisted disease-priority placeholders
```

General parents use source LOINC `81252-9`. Priority parents use their approved
mapping's source key (initially `genomics:<marker>`) and portable LOINC `81252-9`.
The parent retains the gene in `qualifier_source_value` and variant string in
`value_as_string`. Components use `measurement_event_id`/`observation_event_id`
and event-field concepts resolved from installed CDM code
`measurement.measurement_id`. Both patient and event-field type must match.

The approved mapping controls the destination table. A standard concept must
match that domain; portable LOINC codes resolve through the installed vocabulary,
including Maps to. Missing standard mappings use concept 0 with raw source code;
no standard concept IDs are fabricated. Initial component recipes:

| Field | Source code | Table |
|---|---|---|
| gene | 48018-6 | Measurement |
| interpretation | 53037-8 | Measurement |
| genome_assembly | 62374-4 | Measurement |
| transcript_reference_sequence_id | 51958-7 | Measurement |
| amino_acid_change | 48005-3 | Measurement |
| variant_category | 83005-9 | Measurement |
| variant_analysis_method_type | 81304-8 | Measurement |
| genomic_source_class | 48002-0 | Measurement |
| chromosome | 48000-4 | Measurement |
| cytogenetic_location | 48001-2 | Measurement |
| genomic_dna_change | 81290-9 | Measurement |
| allelic_frequency | 81258-6 | Measurement, numeric |
| variant_name, variant_description, origin | genomics:<field> | Observation, raw text |
| assessment, specimen_id, specimen_type, collection_date, report_id, laboratory | genomics:<field> | Observation, raw text |
| interpretation_date, classification_framework, evidence_source, genomic_reference_sequence_id, zygosity | genomics:<field> | Observation, raw text |

Source reference: [LOINC discrete variant panel](https://loinc.org/81250-3/panel).
`variant` preserves the legacy/transcript DNA string separately from the name,
protein change and full description. Input aliases `mutation` and `assay_method`
remain accepted. Component mapping names are `genetic_mutations.<field>`; these
and the concrete priority fields appear in the mapping inventory for curation.

Sample VAF has explicit `%` (0–100) or `1` (0–1) units, maximum five decimal places;
zero is preserved. Origin and genomic source class remain independent. Optional
values stay missing. Invalid dates, numeric values, unknown fields and overlong
inputs are rejected. Text limit: 10,000 characters; gene: 50. A new interactive
entry without test_date uses today; extracted reports must not rely on that default.

Editing retains the parent ID and supersedes known component facts. Deleting
marks parent and linked facts erroneous, retaining them in the database. Reads
recognize legacy gene-specific Measurements and mappings with withdrawn approval;
writes require current approval for populated/cleared components and priority
parents. Parent, components and refresh are atomic under a patient-record lock.
Per-refresh snapshot memoization avoids repeatedly loading genomic mappings.

Migration 0222 widens existing Measurement/Observation text-value columns. This
is a local accommodation, not unmodified CDM conformance: Measurement.value_as_string
is already an application extension. Strict exports must handle long text explicitly,
for example via linked Notes. See [OMOP CDM](https://ohdsi.github.io/CommonDataModel/cdm54.html).

## API, installation and verification

- `GET/POST /api/v1/patient-records/{person_id}/genomics/`
- `GET/PATCH/DELETE /api/v1/patient-records/{person_id}/genomics/{variant_id}/`
- `GET /api/v1/patient-records/{person_id}/genomics-catalog/?disease=BC`
- `PATCH /api/v1/patient-records/{person_id}/` with named lists, for example
  `{"genomics_brca1":[{"gene":"BRCA1","variant":"c.68_69delAG"}]}`.

Legacy patient-info routes share the writer. Named-list PATCH replaces only that
marker; `[]` clears it. IDs must belong to the same patient/marker and cannot repeat.
Do not mix full-list replacement and named-priority edits in one request. Unchanged
full-record projection echoes are ignored. Patient/representative, clinician,
analyst, service-token and organization access use existing authorization and
SMART scopes. Self-reported entries use type 32865; clinician entries use 32817.

Migration 0223 adds 42 list projections and the JSON mapping value kind. Migration
0224 seeds 68 approved storage recipes. `manage.py seed_genomics_catalog` creates
missing recipes idempotently, preserving all existing curator decisions, including
rejections. Approval authorizes storage semantics, not expert clinical validation.
Load required CDM event/type/unmapped concepts before writing. The fixture must be
packaged with the application and kept immutable for migration reproducibility.

Verification uses isolated PostgreSQL databases `promop_genomics_ci` and
`promop_genomics_migrations` on localhost:5433, never production. The full migration
chain and `makemigrations --check --dry-run` pass. Tests cover CRUD, every attribute,
long text, access/scopes, repeated findings, legacy round trips, approval/clears,
marker isolation, fixture idempotency, curation visibility, placeholders/disease
changes and all five disease-tab removals. The refresh query-budget test passes.

## CDEW / NGS review: recommendations and integration gates

[CDEW design PR #101](https://github.com/healthkey-ai/cdew/pull/101) revises Vlad's
§10.3: one finding retains origin, interpretation and VAF together. Gene/date
identities and unlinked origin Observations are unsafe. Use a specialized source
adapter, not list replacement or generic FHIR sync, which currently truncates
strings and does not preserve the genomic component/report graph.

**Not yet implemented:** published import-action schema, source-finding idempotency
and reconciliation (including timeout-after-commit), DOCUMENT_EXTRACTION provenance
adapter and explicit missing-test-date handling. These gate live CDEW genomic
imports; CDEW holds whole findings until support is deployed. Interactive CRUD is
not an idempotent import endpoint.

NGS reports warrant shared report/specimen/assay context: accession namespace,
issued date, preliminary/final/amended status, version/superseded report, panel
name/version, tested regions, tumor purity, coverage, detection limits and limitations.
Current report/specimen fields are per-finding text, not normalized resources.
Keep no-variant reports; a negative result applies only to the assay's tested scope.

Further typed fields should include coordinates/convention, reference/alternate
alleles, HGNC/external IDs, read counts, copy number and fusion partners/breakpoints.
Separate dated pathogenicity, somatic tier and therapeutic implications. TMB/MSI/HRD
are separate assay results, not fake genes or attributes duplicated on every variant.
These are recommendations, not implemented inputs, informed by the
[HL7 overview](https://www.hl7.org/fhir/uv/genomics-reporting/STU3/general.html) and
[variant guidance](https://www.hl7.org/fhir/uv/genomics-reporting/STU3/sequencing.html).

## Questions for genomics experts

- Is CancerBot's PALB1 intended to mean PALB2? Which legacy aliases can safely be normalized?
- Which supplied example variants are valid for each gene and transcript? CancerBot's
  ESR1 examples overlap TP53-style entries; should they be replaced after review?
- Confirm each disease's priority list, including structural findings and whether
  IGHV, BTK/PLCG2 resistance, or other genes should be added beyond CancerBot's list.
- How should unknown, not tested, absent, present and indeterminate be distinguished?
- Which specimen/report identifiers, transcript/assembly versions and classification
  framework details are mandatory before clinical use?
- Should interpretations be a separately versioned history with evidence and
  therapeutic actionability, and how should conflicting laboratories be displayed?
- Which structural-variant coordinates, copy-number units, fusion partners, read-depth
  metrics and population-frequency sources are needed for the next iteration?
