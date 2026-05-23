# TODO

## Code-review: flagged issues (PR #72)

Issues identified during code review that require architectural decisions, profiling, or broader scope changes before fixing. Items marked ✅ were fixed in the review pass.

### _build_cards loads all measurements into memory
- **Severity:** high / performance
- `patient_portal/api/lab_results/views.py` — `ResultsSummaryView._build_cards`
- Fetches ALL measurements for a person, groups in Python, then discards most (MAX_VALUES_PER_CONCEPT=10). A patient with thousands of measurements (common in oncology — CBC panels generate 10+ per draw) loads them all before pagination. The pagination only covers the cards (concepts), not the underlying query.
- **Action:** Restructure to first query distinct concept IDs for the person (paginated), then fetch only measurements for concepts on the current page with a per-concept LIMIT using a window function or separate queries.

### _next_pk holds row locks for entire sync transaction
- **Severity:** medium / performance
- `patient_portal/api/lab_results/sync.py:49-56`
- Every `_next_pk` call acquires a row lock via `select_for_update()` held until the entire `@transaction.atomic` POST completes. 500 measurements = 500+ lock acquisitions serializing all concurrent syncs. Empty table race: if no rows exist, `select_for_update` locks nothing and two concurrent transactions can both create pk=1.
- **Action:** Migrate OMOP tables (Measurement, VisitOccurrence, CareSite, Concept) from manual IntegerField PKs to PostgreSQL sequences via Django's BigAutoField.

### Identity.sub unique=True conflicts with multi-issuer OIDC
- **Severity:** medium / design (architectural blocker)
- `patient_portal/models.py:50`
- `sub` is the Django `USERNAME_FIELD` (requires `unique=True`), but OIDC `sub` is only unique within an issuer. Two issuers with the same `sub` value will collide. The composite `UniqueConstraint` on `(issuer, sub)` is correct but `unique=True` on `sub` alone is more restrictive. Not a problem with a single Firebase provider, but blocks adding a second OIDC provider.
- **Action:** Introduce a synthetic unique field (e.g. `uid = f"{issuer}:{sub}"`) as `USERNAME_FIELD` and remove `unique=True` from `sub`. Requires a careful migration.

### Frontend test coverage missing
- **Severity:** medium / design
- `frontend/src/App.test.tsx` (deleted), no replacements added
- PR deleted all existing frontend test files and jest config. CI now runs only `lint` + `build`. No tests for the new federation hooks (`useLabResultsSummary`, `useLabValues`, `useUpdateMeasurement`, `useDeleteMeasurement`), lab components, or Module Federation boundary behavior.
- **Action:** Add vitest configuration (`vitest.config.ts`), add a `test` script to `package.json`, add a `test` step to CI, and write tests for federation hooks and key lab components.

### Test coverage gaps for authorization edge cases
- **Severity:** medium / correctness
- `patient_portal/api/lab_results/tests.py`
- No tests for: actor_iss/actor_sub on-behalf-of flow, org-scoped sync rejection, pipe character validation in actor fields, concurrent PK generation, PATCH with invalid date, PersonalRepresentative `verification_status` enforcement, ProfessionalGroupAccess `expires_at` enforcement.
- **Action:** Add test cases for these authorization paths.

### Extract shared person auto-provisioning logic (DRY)
- **Severity:** medium / design
- `patient_portal/api/lab_results/sync.py:_resolve_person_from_identity` and `patient_portal/api/authentication.py:_ensure_person`
- Nearly identical logic in two places: check PatientUser, check email match, create Person with max(person_id)+1, create PatientUser. The sync copy previously had a bug the auth copy didn't (missing `transaction.atomic`), now fixed. Keeping two copies will cause drift again.
- **Action:** Extract into a shared `resolve_or_create_person(identity, email=None)` function in `patient_portal/services.py` and call from both places.
