# Mapping Hub & Therapy Mapping — Implementation Plan

**Issues:** #868 (Mapping Hub), #869 (Therapy Mapping CRUD)
**Branch:** `feat/868-869-mapping-hub-therapy-crud`
**Worktree:** `.claude/worktrees/feat-mapping-hub`

---

## Phase 1: Backend — Mapping Stats API

- [x] **1.1** Add `mapping_stats` view in `patient_portal/api/views.py`
  - Returns counts for field mappings (total/approved/proposed)
  - Returns counts for code mappings (total/approved/proposed)
  - Returns counts for therapy data (regimens/components/classes/disease_links)
  - Staff or org_admin only
- [x] **1.2** Register at `GET /api/v1/mapping-stats/` in `v1_urls.py`
- [x] **1.3** Add backend test for mapping stats endpoint

## Phase 2: Backend — Therapy Mapping CRUD API

- [x] **2.1** Extend `therapy_regimen_list` to accept POST (create regimen)
- [x] **2.2** Extend `therapy_regimen_detail` to accept PATCH/DELETE
- [x] **2.3** Add `therapy_regimen_components` view (POST to add, DELETE to remove component)
- [x] **2.4** Extend `therapy_component_list` to accept POST (create component)
- [x] **2.5** Add `therapy_component_classes` view (POST to add, DELETE to remove class link)
- [x] **2.6** Extend `therapy_class_list` to accept POST (create class)
- [x] **2.7** Add `disease_therapy_regimen_list` view (GET list, POST to add)
- [x] **2.8** Add `disease_therapy_regimen_detail` view (DELETE to remove)
- [x] **2.9** Register all new URL patterns in `v1_urls.py`
- [x] **2.10** Add backend tests for therapy CRUD endpoints

## Phase 3: Frontend — Mapping Hub Page

- [x] **3.1** Create `frontend/src/api/mappingHub.ts` — API client for stats + therapy CRUD
- [x] **3.2** Create `frontend/src/components/MappingHub/MappingHubPage.tsx`
  - Back button, title "Mapping Administration"
  - 3 cards: Field Mapping (Database icon), Code Mapping (Braces icon), Therapy Mapping (FlaskConical icon)
  - Each card shows stats and links to its page
- [x] **3.3** Update `frontend/src/App.tsx` — add `/mappings` route with `mappingAdminRoute`
- [x] **3.4** Update `frontend/src/components/Patient/PatientList.tsx`
  - Replace "Field Mappings" + "Code Mapping" buttons with single "Mappings" button (Globe icon)

## Phase 4: Frontend — Therapy Mapping Page

- [x] **4.1** Create `frontend/src/components/TherapyMappings/TherapyMappingPage.tsx`
  - Tab 1: Regimen-Component — list regimens, expand to see components, add/remove
  - Tab 2: Component-Class — list components with class tags, add/remove
  - Tab 3: Disease-Round-Regimen — list associations, add/remove
- [x] **4.2** Add `/therapy-mappings` route in App.tsx with `mappingAdminRoute`

## Phase 5: Verification

- [x] **5.1** `npm run lint` — no errors
- [x] **5.2** `npx tsc --noEmit` — no type errors
- [x] **5.3** `npm test -- --run` — frontend tests pass
- [x] **5.4** Backend Django tests pass (19 new tests, all pass)
- [x] **5.5** Commit, push, create PR (#873)
- [x] **5.6** Code review (auto-fixed 6 issues, user approved 2 more)
- [x] **5.7** Merge PR (merged, branch deleted)
