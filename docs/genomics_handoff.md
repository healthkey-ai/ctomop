# Genomics handoff for Claude

Snapshot: 2026-09-11. The user explicitly requested a handoff before further work.
**Stop condition for this session: document and preserve; do not merge now.**
Only Genomics and its CancerBot/CDEW integration are in this handoff.

## 1. User intent / completion criteria

The original request authorized issues, implementation on an own branch, an
implementation plan converted to `genomics_architecture.md`, isolated-DB tests,
review, PR and merge to `dev`. The user subsequently asked to:

- File suspected CancerBot issues and assign them to `SamarElkassas`.
- Review Vlad's CDEW `docs/promop-alignment.md` §10.3, recommend NGS design changes,
  edit CDEW's design and open a PR for him. **No authorization to merge CDEW's PR.**
- Ensure gene/mutation editing is removed from the second/disease tab for all
  five diseases, with editing centralized on Genomics.
- Finally pause and document **all remaining Genomics work** for Claude.

Core feature: full variant CRUD; disease-specific empty priority rows; list columns
Gene/Mutation/Origin/Interpretation; row-click dialog with all detailed attributes;
real named PatientRecord field mappings writing through approved recipes to OMOP
Measurements/Observations. BC includes BRCA1, BRCA2, PIK3CA and TP53 even without data.

## 2. Repositories, branches and PRs

### PRomop

- Workspace: `/Users/adamblum/promop`.
- Branch: `feat/disease-genomics`, pushed to origin.
- Open implementation PR: **https://github.com/healthkey-ai/promop/pull/1188**.
- Last pushed head: `cdad33ca9e4f83918f9107b37d4e1d1362d65aa4`.
- Commits: `2bf7a70` original implementation plan; `9034cc0` feature;
  `cdad33c` merge latest dev, resolve overlap and add mapping-admin Genomics tab.
- Base at snapshot: `e8c69e672affbd06e8fdd3666141ab7d9f98895a`.
- PR was open and mergeable, but `mergeable_state=unstable` because CI is not green.
- Issues #1179 (canonical CRUD/OMOP), #1180 (priority mappings/catalog), #1181
  (dialog/architecture/tests) are referenced with closing keywords by PR #1188.
- Authoritative architecture: root **`genomics_architecture.md`**. This handoff is
  operational state, not a replacement for that architecture.

### CDEW

- Open **documentation-only** PR: https://github.com/healthkey-ai/cdew/pull/101.
- Reviewer requested successfully: **`vtrv101` (Vladimir/Vlad Tarasov)**.
- Branch: `docs/ngs-genomics-contract`, head `06dad77` (pushed).
- Isolated checkout: `/private/tmp/cdew-genomics.bGfTPD/repo`.
- User's normal `/Users/adamblum/cdew` checkout was only read, not edited.
- Changed `docs/promop-alignment.md`; added `docs/genomics-integration.md`.
- Eight embedded JSON examples were parsed successfully; NGS example keys were
  checked against the PRomop fixture; its source span length matches its snippet.
- Leave this PR for Vlad; do not merge it as part of the PRomop merge.

### CancerBot

- Read-only source checkout: `/Users/adamblum/cancerbot`.
- Source catalog pinned at `a840f8d9af2c35477e2b6b76f981b29f02c21eec`.
- Existing PALB naming issue assigned, avoiding a duplicate:
  https://github.com/cancerbot-org/cancerbot/issues/4812.
- New ESR1/PIK3CA example-validation issue:
  https://github.com/cancerbot-org/cancerbot/issues/5297.
- New per-disease option-subset review issue:
  https://github.com/cancerbot-org/cancerbot/issues/5298.
- All three assigned successfully to **`SamarElkassas`**. GitHub's assignment check
  was case-sensitive: lowercase `samarelkassas` returned 404, canonical casing worked.
- The new issue bodies' line-break formatting was corrected after creation.

## 3. Implemented and committed

- Shared Genomics component in both standalone and federated patient views.
- Full CRUD using a detail dialog, delete confirmation, errors/loading/read-only
  handling, keyboard row activation and optional arbitrary gene symbols.
- 42 disease-priority marker keys across MM/FL/BC/MCL/CLL, backed by real
  `PatientRecord.genomics_<key>` JSON lists. Repeated findings are not flattened.
- Versioned fixture `omop_core/data/genomics_catalog_v1.json`, containing the
  disease catalog and 26 component mappings; **68 seeded approved mappings total**.
- Priority placeholders are presentation only. No clinical facts are inserted
  merely because the disease has a priority gene. Changing disease preserves data.
- Named priority PATCH routes through canonical OMOP writes; an empty list clears
  only that marker. The full general `genetic_mutations` projection remains.
- Approved FieldConceptMappings govern priority parent and component writes.
  Parent and components are written atomically under the patient-record lock;
  deletes/superseded components use `is_erroneous`, retaining database records.
- Long text storage, source-preserving concept-0 fallbacks, vocabulary/domain
  validation, patient/marker ownership checks, legacy reads and SMART authorization.
- Mapping admin now has a Genomics category and exposes nested component mappings
  (`genetic_mutations.origin`, etc.). Serializer allows only recognized component
  paths, not arbitrary dotted field names.
- Disease tab has no BC mutation form, MCL molecular-markers input, MM cytogenetic
  abnormalities input or CLL/MCL TP53-disruption input. Disease selection remains.
  Cytogenetic *risk classification* and protein-expression biomarkers are separate.
- Regression tests cover all five disease-tab removals even with stored data and
  writable descriptors. Shared component guarantees the same behavior in both views.
- Clearer UI labels: sample variant allele frequency (VAF), protein/amino-acid change.
- Root architecture includes additional NGS recommendations and expert questions.

Important implementation files:

- `frontend/src/components/PatientInfo/tabs/GenomicsTab.tsx` and its tests.
- `frontend/src/components/PatientInfo/tabs/DiseaseTab.tsx` and its tests.
- `frontend/src/components/Patient/PatientDetail.tsx`, `frontend/src/federation/PatientInfo.tsx`.
- `frontend/src/components/FieldMappings/FieldMappingPage.tsx` and its tests.
- `omop_core/services/genomics.py`, `genomics_catalog.py`, `patient_record_service.py`.
- `omop_core/services/field_descriptor.py`, `write_descriptor.py`.
- `patient_portal/api/views.py`, `permissions.py`, `serializers.py`.
- `tests/test_genomics_crud.py`, `test_genomics_catalog.py`, `test_genetic_mutation_roundtrip.py`.

## 4. Uncommitted work: preserve and finish first

At handoff, two existing files have intentional uncommitted Genomics changes:

1. `omop_core/services/patient_record_service.py`:
   - `_get_genomics_pathology_data` filters explicit absent/not_tested/no_call/
     indeterminate findings out of the legacy `molecular_markers` detected summary.
   - `_compute_derived_fields` only sets TP53 disruption from a pathogenic TP53
     finding whose assessment is absent/blank in the legacy sense (`None` or `''`)
     or explicitly `present`. It case-folds interpretation so `Pathogenic` works.
   - Here “absent/blank in the legacy sense” means **missing assessment**, not the
     explicit assessment string `absent`, which must NOT count as detected.
2. `tests/test_genomics_catalog.py` adds four parameterized regression cases for
   assessment `absent`, `not_tested`, `no_call`, `indeterminate`. Each verifies the
   result stays in the Genomics projection without becoming TP53 disruption or a
   detected marker; changing that finding to `present` makes the derived flags true.

The final local run passed all four new assessment tests. These changes are
important: permitting explicit negative/no-call results must
not make downstream summaries treat them as detected mutations. They are **not
yet in the pushed PR**. Review, test, commit and push them before merge.

Further review questions (not verified defects):

- Existing TP53-disruption derivation returns False when there are no findings.
  That legacy behavior is unchanged; consider whether expert-approved semantics
  should instead distinguish unknown from negative. Do not silently widen this fix.
- Check present→nonpositive transitions clear the legacy summary as well as the
  inverse direction already in the new tests. `_clear_derived_fields` normally clears it.
- Legacy aggregate-only molecular/cytogenetic data is not automatically converted
  into fabricated discrete variants. Confirm historical display/import expectations;
  the canonical legacy reader handles gene-specific Measurements, not every possible
  free-text genomic statement in arbitrary Observations.

## 5. CI blockers: false positive and merged-base startup tests

Current CI run: **34584325610** on head `cdad33c`.
https://github.com/healthkey-ai/promop/actions/runs/34584325610

- Frontend lint/build: success.
- Async derivation e2e: success.
- CodeQL / Analyze actions, Python, JS/TS: success.
- Backend tests: still running at last poll; check final result.
- Security gates: failed **only Secret scan (gitleaks)**. Dependency audit and both
  Bandit scans passed (zero new findings).

Gitleaks flagged the literal catalog entry **`"key": "bcl2_amplification"`** at
`omop_core/data/genomics_catalog_v1.json:487` as `generic-api-key`.
This is a genomic marker identifier, **not a credential**.
Fingerprint:
`9034cc0b85e0a714287feaa055d9f20b7a9fe00d:omop_core/data/genomics_catalog_v1.json:generic-api-key:487`.
Security job ID: `103214906346`.

Recommended next step: add a narrowly documented `.gitleaks.toml` allowlist scoped
to **generic-api-key AND this exact fixture path AND this exact marker value**.
Use explicit AND semantics; do not disable the rule or ignore the whole fixture.
Check gitleaks 8.30.1 syntax (`targetRules`, `condition`, `regexTarget`, exact regex)
and run the history scan locally/CI. Removing/renaming the current literal alone
does not fix history scanning; the earlier commit is scanned too. No allowance
or security configuration change has been made yet.

The final local suite also found **two deployment-startup failures from merged dev**:
`tests/test_deployment_startup_contract.py::test_production_uses_bounded_database_preparation_before_gunicorn`
and `::test_render_requires_the_athena_source_for_the_web_service`.
They expect `python manage.py prepare_production_database --gdrive` in `start.sh`
and `ATHENA_VOCABULARY_GDRIVE_URL` in the Render web-service configuration. Neither
is present. Verified `git diff origin/dev -- start.sh render.yaml` is empty: the
Genomics branch did not change those files relative to its merged base. This is
not a reason to bypass CI. Coordinate/use the upstream startup correction, or
investigate in a separate scoped fix; the user asked to hand off Genomics now.

## 6. Test evidence and running process

All database testing used isolated local PostgreSQL, not production.

- Before merging latest dev: full pytest **1597 passed, 3 skipped, 2 deselected**.
- Before dev merge: frontend **509 passed, 4 skipped**, lint/build passed.
- After dev merge + mapping-admin category: frontend **512 passed, 4 skipped**,
  lint, type-check and production build passed. Three unrelated existing React hook
  warnings and Vite bundle-size warnings remain.
- Full fresh migration chain passed; `makemigrations --check --dry-run` passed.
- After dev merge, the extra migration branch and merge migration also applied
  successfully on the isolated migration database; no model/migration drift.
- Earlier full Django runner: 2042 tests, 39 skipped, **one failure** in
  `omop_core.tests.RefreshQueryCountTest.test_query_count_under_budget` (22 > 20).
  Fixed with per-snapshot Genomics projection memoization; targeted test subsequently
  passed together with 46 catalog/descriptor tests. CI now reruns the full runner.
- Widening text fields initially broke three benchmark Coalesce tests; fixed with
  explicit output_field in `benchmark_trial_eligibility.py`; full pytest passed after.

**Last local full pytest completed: 1728 passed, 2 failed, 3 skipped, 2 deselected.**
The two failures are the merged-base startup contract tests described above, not
Genomics tests. This run includes the uncommitted assessment guard and latest dev schema:

```bash
DATABASE_URL=postgresql://adamblum@localhost:5433/promop_genomics_ci \
  .venv/bin/pytest -q --create-db --tb=short
```

Codex unified execution session ID was **58406**, now completed (exit 1).
There is no remaining local test process from this run.
Do not run two test suites concurrently against the same test DB.

Databases (local user `adamblum`, port 5433):

- `promop_genomics_ci`, pytest creates `test_promop_genomics_ci`.
- `promop_genomics_migrations`, used for actual migrations; the prior Django runner
  created/destroyed `test_promop_genomics_migrations` normally.

**Always explicitly set DATABASE_URL.** The repository `.env` may point at a remote
production database. Never source it and run migrations/tests without overriding
the URL. No live/production migrations or patient data writes were performed.

## 7. Merge history pitfalls

`dev` advanced during this work. Merging it required more than deleting conflict
markers: upstream overlapping edits restored a legacy variant writer and removed
the standalone Genomics tab. `cdad33c` explicitly restored the new canonical writer,
the standalone tab, and removed the obsolete handlers while retaining upstream
profile-editing fixes. Recheck these if another dev merge is required.

Migrations currently:

- `0222_genomics_text_values` → `0223_priority_genomic_fields` →
  `0224_seed_genomics_mappings`.
- Upstream `0222_trial_favorites_and_search_preferences` →
  `0223_backfill_approved_suggestion_outcomes`.
- **`0225_merge_genomics_and_suggestion_backfill` joins both leaves.**

The JSON fixture is under an otherwise ignored data directory; it was explicitly
force-added and is tracked in Git. Ensure it remains packaged with the application.
Do not silently rewrite frozen v1 migration data once deployed; version future changes.

## 8. Remaining PRomop completion checklist

1. Preserve/review the two uncommitted assessment files; the latest full local
   result is recorded above. Add present→negative clearing coverage if needed.
2. Fix the exact gitleaks false positive with a narrowly scoped, tested allowance.
3. Resolve/coordinate the merged-base startup test failures without bypassing CI.
   Record the final merged-schema test counts and update PR #1188's test evidence
   (its body currently quotes pre-merge counts). Mention migration 0225 in architecture.
4. Commit/push the assessment guard, security allowance and final docs after checks.
5. Re-run/review full CI: backend migrations + Django runner + pytest; frontend;
   real-broker e2e; security; CodeQL. Do not bypass red gates.
6. Review the full diff against current dev, especially authorization, linked-fact
   deletion, mapping approval, arrays/clear behavior and no mutation editors on tab 2.
   No independent human approval is claimed; work so far was local self-review and tests.
7. When the user resumes and all gates pass, complete the originally authorized
   PRomop merge to dev. Leave CDEW #101 open for Vlad. Report merge SHA and results.

## 9. NGS/CDEW remaining design and implementation work

The current feature is interactive CRUD, **not a safe automated import endpoint**.
CDEW PR #101 describes these explicit receiving gates; they are not implemented:

- Published, versioned Genomics custom-action schema/capability contract (current
  custom DRF actions cannot simply be inferred from generic OMOP serializers).
- Server-side source-finding idempotency and reconciliation: organization, patient,
  source system, report identity/version, stable finding identity. Handle concurrent
  retry, timeout after commit, extractor-version reruns and amendments/retractions.
- DOCUMENT_EXTRACTION provenance adapter, source document/extraction/reviewer
  references; rich spans remain CDEW-owned. Current payload rejects extra `source`
  or arbitrary provenance fields rather than pretending to persist them.
- Explicit missing-test-date policy. Interactive creates currently default to today;
  CDEW must hold undated findings instead of dating them to extraction/upload time.
- CDEW runtime `genomic_variant` object, source schema snapshot, review and specialized
  commit adapter; whole findings held until receiving gates pass. Named PatientRecord
  list replacement is **not** an incremental import API.

Generic FHIR sync is unsuitable today: `_parse_obs` truncates strings to 60 chars;
discrete Observation dedup omits variant text/report/specimen identity; genomic
components and report relationships are not ingested. A future FHIR Genomics graph
adapter is possible but needs its own explicit contract and round-trip tests.

Proposed additional data model (recommended, **not implemented**):

- Shared report/specimen/assay resources: accession namespace/ID, report issued date,
  status, version/supersession, panel/version, actual tested genes/regions, tumor
  content/purity, read coverage, detection limits and limitations.
- Preserve no-variant reports; negative findings apply only within tested scope.
- Coordinates/convention, reference/alternate alleles, HGNC/external variant IDs,
  read depth/alternate reads, copy number, fusion partners/breakpoints.
- Separate dated pathogenicity classification, somatic evidence tier and therapeutic
  implications/actionability. Avoid one undifferentiated interpretation string.
- TMB/MSI/HRD as separate assay results, not invented genes or duplicated variant attrs.

Current implemented extras already include specimen/report IDs, laboratory,
collection/interpretation dates, classification framework/evidence, genomic reference
sequence ID, zygosity and explicit assessment. See root architecture for the full
field/table mapping and expert questions. Keep API names compatible while clarifying
labels (sample VAF, transcript DNA change, protein change). Do not infer protein
consequence, origin or zygosity from insufficient evidence.

Wait for Samar's source-catalog answers and Vlad's design review before silently
changing nomenclature or treating these recommendations as approved clinical rules.
