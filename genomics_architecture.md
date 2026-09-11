# Genomics implementation plan

Status: implementation in progress. This document will become the as-implemented
architecture after verification and review.

## Scope and delivery

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
7. Review the complete diff, create a PR to dev, pass CI and merge. Rewrite this
   file to describe the delivered architecture, test evidence and open expert questions.

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
