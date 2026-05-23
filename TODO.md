# TODO

## Code-review: flagged issues (2026-05-23, branch feat/hk-labs-integration)

### ~~[CRITICAL] Login broken — USERNAME_FIELD='uid' vs email-based authenticate()~~ ✅ FIXED
- Added `patient_portal/backends.py` with `EmailBackend` (looks up by `email__iexact` + `issuer="urn:local"`)
- Registered in `AUTHENTICATION_BACKENDS` in `ctomop/settings.py`

### ~~[CRITICAL] Superusers denied access to all lab result endpoints~~ ✅ FIXED
- Added `if getattr(actor_identity, 'is_superuser', False): return True` at top of `can_access_patient()` in `omop_core/authorization.py`

### ~~[HIGH] PatientDetail displays "undefined undefined" for patient name~~ ✅ FIXED
- Updated `PatientDetail.tsx` to use `user.name || user.email` matching `UserSerializer` shape

### ~~[HIGH] ~16 clinical fields unreachable after tab refactor~~ ✅ FIXED
- Added 10 model-backed fields to new tabs: GeneralTab (medical history + infection status), LabsTab (diagnostic tests), DiseaseTab MyelomaSection (measurable_disease_imwg)
- Fixed 6 stale TS type names in `patient.ts` to match actual API field names (e.g. `active_malignancies` → `no_other_active_malignancies`)
- Removed 6 phantom fields from TS types that never existed in the model (`m_protein_serum`, `m_protein_urine`, `num_lesions`, `clonal_plasma_percent`, `lvef_percent`, `toxicity_grade_maximum`)

### ~~[HIGH] Identity.save() uid not added to update_fields — latent desync~~ ✅ FIXED
- `Identity.save()` now appends `"uid"` to `update_fields` when specified, ensuring uid stays in sync with issuer:sub

### ~~[MEDIUM] useAuth User interface type mismatch~~ ✅ FIXED
- Updated `User` interface in `useAuth.ts` to `{id, sub, email, name}` matching `UserSerializer`

### ~~[MEDIUM] _next_pk race condition on empty table~~ ✅ FIXED
- Replaced `select_for_update()` with `LOCK TABLE ... IN EXCLUSIVE MODE` to guarantee serialization even on empty tables

### ~~[LOW] (Pre-existing) Dashboard view uses nonexistent read_at field~~ ✅ FIXED
- Changed `read_at__isnull=True` to `is_read=False` in `patient_portal/views.py`

### ~~[LOW] (Pre-existing) Admin search_fields references nonexistent username~~ ✅ FIXED
- Changed `patient_user__username` to `patient_user__identity__email` in `patient_portal/admin.py`

---

## Prior code-review: flagged issues (PR #72)

### _next_pk holds row locks for entire sync transaction
- **Severity:** medium / performance
- `patient_portal/api/lab_results/sync.py:49-56`
- Every `_next_pk` call acquires a row lock via `select_for_update()` held until the entire `@transaction.atomic` POST completes. 500 measurements = 500+ lock acquisitions serializing all concurrent syncs. Empty table race: if no rows exist, `select_for_update` locks nothing and two concurrent transactions can both create pk=1.
- **Action:** Migrate OMOP tables (Measurement, VisitOccurrence, CareSite, Concept) from manual IntegerField PKs to PostgreSQL sequences via Django's BigAutoField.

