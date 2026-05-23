# TODO

## Code-review: flagged issues (PR #72)

Issues identified during code review that require architectural decisions, profiling, or broader scope changes before fixing. Items marked ✅ were fixed in the review pass.

### ✅ Test coverage gaps for authorization edge cases
- **Fixed:** Added 6 test classes (17 tests) covering: on-behalf-of actor flow, org-scoped sync rejection, pipe character validation, PATCH with invalid date, PersonalRepresentative verification_status enforcement, ProfessionalGroupAccess expires_at enforcement.

### ✅ Extract shared person auto-provisioning logic (DRY)
- **Fixed:** Extracted `resolve_or_create_person(identity, email=None)` into `patient_portal/services.py`. Both `_ensure_person` (authentication.py) and `_resolve_person_from_identity` (sync.py) now delegate to it.

### _next_pk holds row locks for entire sync transaction
- **Severity:** medium / performance
- `patient_portal/api/lab_results/sync.py:49-56`
- Every `_next_pk` call acquires a row lock via `select_for_update()` held until the entire `@transaction.atomic` POST completes. 500 measurements = 500+ lock acquisitions serializing all concurrent syncs. Empty table race: if no rows exist, `select_for_update` locks nothing and two concurrent transactions can both create pk=1.
- **Action:** Migrate OMOP tables (Measurement, VisitOccurrence, CareSite, Concept) from manual IntegerField PKs to PostgreSQL sequences via Django's BigAutoField.

