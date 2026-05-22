# Role Model & Access Control

## Overview

HealthKey uses a role-based access control (RBAC) system with patient groups
as the unit of authorization. Professionals (admin, navigator, doctor) are
granted access to patient groups. Patients control their own data and can
grant professionals access by accepting invitations or inviting them directly.

This model applies in both operating modes:
- **Integrated**: roles stored in the shared database (ctomop), resolved
  from the Identity record
- **Standalone**: roles stored in the service's local database, same schema

---

## Roles

| Role | Can upload/modify PHR | Can create patients | Can manage groups | Can invite professionals | Scope |
|---|---|---|---|---|---|
| **admin** | Yes (on behalf of group patients) | Yes | Yes | Yes | All patients in assigned groups |
| **navigator** | Yes (on behalf of group patients) | Yes | No | No | Patients in assigned groups |
| **doctor** | Yes (on behalf of group patients) | Yes | No | No | Patients in assigned groups |
| **patient** | Yes (own + represented persons) | Yes (represented persons) | No | Yes (grant access to professionals) | Own data + personal representatives |

### Role Semantics

**admin** — organization administrator. Full access to all patients in their
assigned groups. Can create patient groups, assign patients to groups, and
invite other professionals.

**navigator** — patient navigator / care coordinator. Uploads labs, modifies
PHR records on behalf of patients in their assigned groups. Cannot create or
modify groups themselves.

**doctor** — clinician. Same access as navigator: upload/modify PHR on behalf
of group patients. Separated from navigator for audit trail clarity and
potential future permission differentiation.

**patient** — the data owner. Can upload and modify their own PHR. Can join
the system independently or be invited by a professional. Can grant access
to professionals (invite a navigator/doctor to manage their records).

A patient may also act as a **personal representative** for other people:
a minor child, elderly parent, family member, friend, etc. In this case
one Identity manages multiple Person records. See "Personal Representatives"
below.

---

## Personal Representatives

A user joining as a patient may not be managing only their own health records.
Common scenarios:

- Parent managing a minor child's PHR
- Adult child managing an elderly parent's PHR
- Spouse or partner managing records for a family member
- Friend or caregiver helping someone who cannot self-manage

### Model

```
PersonalRepresentative
  representative    — FK → Identity (the person who manages)
  person            — FK → Person (whose PHR is being managed)
  relationship      — free text or enum: parent, child, spouse, guardian, caregiver, other
  granted_at
  granted_by        — FK → Identity (who authorized this: self, the patient, or an admin)

  UNIQUE(representative, person)
```

A personal representative has the same rights as the patient themselves:
upload, modify, view the represented person's PHR. They are not professionals
and do not need group-based access — the relationship is direct,
person-to-person.

### How It Works

When a user authenticates:
- Their Identity resolves to their own Person (via PatientUser) — optional,
  they may not have their own PHR
- PersonalRepresentative records give them access to additional Person records

The effective patient set for a patient-role user is:
```
own Person (if exists) + all Person records where they are representative
```

### Joining to Represent Someone Else

```
1. User authenticates → Identity created
2. User indicates they are joining to manage someone else's records
3. System creates a new Person for the represented individual
4. PersonalRepresentative record links Identity → new Person
5. User can now upload/modify PHR for that Person
6. Optionally: user also creates their own Person record (own PHR)
```

A single user can represent multiple people (e.g. parent with two children)
and also manage their own PHR.

### Authorization Check (Updated)

```python
def can_access_patient(actor_identity: Identity, target_person_id: int) -> bool:
    """Check if actor has access to target patient."""
    # Self-access
    try:
        if actor_identity.patient_user.person_id == target_person_id:
            return True
    except PatientUser.DoesNotExist:
        pass

    # Personal representative
    if PersonalRepresentative.objects.filter(
        representative=actor_identity,
        person_id=target_person_id,
    ).exists():
        return True

    # Professional group access
    actor_groups = ProfessionalGroupAccess.objects.filter(
        identity=actor_identity,
    ).values_list('group_id', flat=True)

    return PatientGroupMembership.objects.filter(
        group_id__in=actor_groups,
        person_id=target_person_id,
    ).exists()
```

### Provenance for Representative Actions

When a representative uploads/modifies PHR:
- `source` = `PATIENT_SELF` (they are acting with patient-level authority)
- `source_user_id` = representative's `issuer|sub`
- `target_patient_id` = represented person's person_id

This distinguishes from professional on-behalf-of actions
(`source=ADMIN_CORRECTION`) in the audit trail.

---

## Patient Groups

Patients are organized into groups. A group is an arbitrary collection of
patients, defined by the organization for operational purposes:

- Disease cohort (e.g. "Multiple Myeloma patients")
- Location (e.g. "Bay Area clinic")
- Care team (e.g. "Dr. Smith's patients")
- Clinical trial (e.g. "Trial NCT-12345 participants")
- Any other organizational grouping

A patient can belong to multiple groups. A professional can be granted access
to multiple groups.

### Group Membership: Manual and Rule-Based

Group membership can be managed two ways:

**Manual assignment** — a professional with group access adds a patient
explicitly. This is the default for ad-hoc groupings (care teams, clinic
rosters).

**Rule-based auto-assignment** — the host app defines rules that
automatically assign patients to groups based on clinical or demographic
criteria. Examples:

- Diagnosis: patient with ICD-10 C90.0 (Multiple Myeloma) auto-joins
  the "Multiple Myeloma" group
- Location: patient with zip code 94xxx auto-joins "Bay Area" group
- Trial enrollment: patient enrolled in NCT-12345 auto-joins the trial group
- Lab result threshold: patient with eGFR < 60 auto-joins "CKD monitoring"

Rules are defined and executed by the host app, not by HealthKey services.
HealthKey provides the group membership API. The host app calls it when
its rules trigger (on patient creation, diagnosis change, lab result, etc.).

This keeps HealthKey services domain-agnostic. The host app owns the business
logic for what constitutes a group and when patients move between groups.
HealthKey services only see the resulting memberships.

### Group Model

```
PatientGroup
  id              — PK
  organization    — FK → Organization
  name            — display name
  slug            — URL-safe identifier
  description     — optional
  rule_managed    — boolean (true if membership is managed by host app rules)
  created_at
  created_by      — FK → Identity (who created the group)

PatientGroupMembership
  group           — FK → PatientGroup
  person          — FK → Person (OMOP)
  source          — enum: manual | rule
  added_at
  added_by        — FK → Identity (NULL when source=rule)

  UNIQUE(group, person)
```

`rule_managed` on PatientGroup signals that the host app controls membership.
Professionals can still view members but should not add/remove manually
(the host app's rules are the source of truth). Groups with
`rule_managed=False` allow manual management by professionals with access.

### Professional Access Grants

```
ProfessionalGroupAccess
  identity        — FK → Identity (the professional)
  group           — FK → PatientGroup
  role            — enum: admin | navigator | doctor
  granted_at
  granted_by      — FK → Identity

  UNIQUE(identity, group)
```

A professional's effective patient set is the union of all patients in all
groups they have access to.

---

## Authorization Logic

### Self-Upload (Patient)

```
actor authenticates → resolve Identity
Identity → PatientUser → Person
actor.person_id == target_person_id → ALLOW
```

No group check needed. Patients always have full access to their own PHR.

### On-Behalf-Of (Professional)

```
actor authenticates → resolve Identity
actor Identity → ProfessionalGroupAccess → list of group IDs
target_person_id → PatientGroupMembership → list of group IDs
INTERSECT → if non-empty → ALLOW
```

The professional must have at least one group in common with the target
patient. The role on ProfessionalGroupAccess determines what they can do
(currently all professional roles have the same permissions, but the model
supports future differentiation).

### Request Flow

```
POST /api/v1/labs/uploads/{id}/commit/
  Authorization: Bearer <firebase-token>
  X-On-Behalf-Of: <person_id>        ← optional, for on-behalf-of

hk-labs:
  1. Authenticate actor (Firebase token → Identity)
  2. If X-On-Behalf-Of present:
       target_person_id = header value
       Pass (actor_iss, actor_sub, person_id) to ctomop
     Else:
       Pass (actor_iss, actor_sub) to ctomop (self-upload)

ctomop sync endpoint:
  1. Resolve actor identity
  2. If person_id provided (on-behalf-of):
       Validate actor has group access to target person
       Record provenance: actor=identity, target=person_id, source=ADMIN_CORRECTION
     Else:
       Resolve person from actor identity (self-upload)
       Record provenance: actor=identity, target=self, source=PATIENT_SELF
  3. Create measurements
```

---

## Invitation Flows

### Professional Creates Patient and Invites

```
1. Professional (admin/navigator/doctor) creates a new Person record
2. Professional assigns Person to one of their groups
3. System generates invitation (email or link)
4. Patient receives invitation → authenticates via IdP → Identity created
5. PatientUser links Identity → Person
6. Patient can now view/modify their own PHR
```

The professional must have group access before they can create patients in
that group.

### Patient Joins Independently

```
1. Patient authenticates via IdP → Identity created
2. Person auto-provisioned (or matched by email to existing record)
3. PatientUser links Identity → Person
4. Patient uploads/manages own PHR
5. Patient can later invite a professional:
     - System creates ProfessionalGroupAccess if the professional's Identity exists
     - Or generates an invitation link for the professional to claim
```

### Patient Grants Access to Professional

```
1. Patient initiates "grant access" flow
2. Patient selects or invites a professional (by email or link)
3. System creates ProfessionalGroupAccess:
     identity = professional
     group = patient's group (or a new per-patient group is created)
     role = navigator | doctor
     granted_by = patient's Identity
4. Professional can now upload/modify on behalf of that patient
```

When a patient grants access and doesn't belong to an explicit group, the
system creates a personal group (one member: the patient). This keeps the
authorization model uniform — all access goes through groups.

---

## Provenance Recording

Every write records who performed the action:

```
ProvenanceRecord
  source              — PATIENT_SELF | ADMIN_CORRECTION | DOCUMENT_EXTRACTION | ...
  source_user_id      — actor Identity (issuer|sub)
  target_patient_id   — person_id of the patient whose data changed
  modification_reason — optional text
  organization        — FK → Organization
  content_type        — FK → ContentType (what was modified)
  object_id           — PK of the modified record
  created_at
```

For on-behalf-of writes:
- `source` = `ADMIN_CORRECTION` (professional acting on behalf)
- `source_user_id` = professional's `issuer|sub`
- `target_patient_id` = patient's person_id

For self-uploads:
- `source` = `PATIENT_SELF` or `DOCUMENT_EXTRACTION`
- `source_user_id` = patient's `issuer|sub`
- `target_patient_id` = same person_id

---

## Storage

### Integrated Mode (Shared Database)

All role/group/access tables live in the shared ctomop database:
- `PatientGroup`
- `PatientGroupMembership`
- `ProfessionalGroupAccess`

Both hk-labs and ctomop query these tables for authorization. hk-labs calls
ctomop's authorization endpoint (or queries directly if sharing the DB).

### Standalone Mode (Local Database)

Same schema, same tables, local to each service. In standalone mode the
service manages its own users and groups independently.

---

## Implementation Notes

### Database Tables

All new tables belong to the `omop_core` Django app in ctomop (since they
reference Person and Organization). In standalone mode for hk-labs, equivalent
tables would live in the `accounts` app.

### API Endpoints (ctomop)

```
# Groups
GET    /api/groups/                         — list groups (filtered by actor's access)
POST   /api/groups/                         — create group (admin only)
GET    /api/groups/{id}/                    — group detail + members
POST   /api/groups/{id}/members/            — add patient to group (manual)
DELETE /api/groups/{id}/members/{person_id}/ — remove patient from group

# Rule-managed membership (called by host app)
POST   /api/groups/{id}/members/sync/       — bulk sync members for rule-managed group
  Body: { "person_ids": [1, 2, 3] }
  Adds missing members (source=rule), removes members no longer in the list.
  Only allowed on groups with rule_managed=True.
  Authenticated via service token (host app → ctomop).

# Access grants
GET    /api/groups/{id}/access/             — list professionals with access
POST   /api/groups/{id}/access/             — grant professional access
DELETE /api/groups/{id}/access/{identity_id}/ — revoke access

# Invitations
POST   /api/invitations/                    — create invitation (patient or professional)
POST   /api/invitations/{token}/accept/     — accept invitation
```

### Host App Integration (Rule-Based Groups)

The host app defines rules for automatic group membership. HealthKey services
provide the group and membership APIs but do not evaluate rules themselves.

```
Host app (e.g. ht-phr)
  │
  ├─ Patient created or diagnosis updated
  ├─ Host app evaluates its rules:
  │    "ICD-10 C90.0 → group 'multiple-myeloma'"
  │    "zip 94xxx → group 'bay-area'"
  │
  └─ Calls ctomop:
       POST /api/groups/{id}/members/sync/
       Authorization: Bearer <service-token>
       Body: { "person_ids": [updated list] }
```

This separation means:
- HealthKey services are domain-agnostic (no disease or geography logic)
- The host app owns all business rules for patient classification
- Different host apps can define completely different grouping criteria
- Rules can trigger on any event the host app knows about: diagnosis,
  lab results, enrollment, location change, etc.

### Authorization Check Helper

See `can_access_patient()` in the "Personal Representatives" section above.
It checks all three access paths: self, personal representative, and
professional group access.

### hk-labs Integration

hk-labs does NOT store roles or groups locally in integrated mode. It passes
the on-behalf-of person_id to ctomop and ctomop validates access. The flow:

1. hk-labs receives upload/commit with `X-On-Behalf-Of: <person_id>`
2. hk-labs passes `person_id` + `actor_iss` + `actor_sub` to ctomop sync
3. ctomop runs `can_access_patient()` before creating measurements
4. ctomop returns 403 if access denied

In standalone mode, hk-labs runs its own copy of the authorization tables
and validates locally.

---

## Future Considerations

- **Permission differentiation by role**: Currently admin/navigator/doctor
  have identical write permissions. The model supports adding granular
  permissions (e.g. doctor can modify clinical notes, navigator cannot).

- **Time-limited access**: Add `expires_at` to ProfessionalGroupAccess for
  temporary grants (clinical trial duration, consult period).

- **Audit log**: ProfessionalGroupAccess changes (grant/revoke) should be
  logged for compliance.

- **Group hierarchy**: Groups could nest (e.g. "All Bay Area" contains
  "Bay Area Clinic A" and "Bay Area Clinic B"). Not needed initially.

- **FHIR Consent**: Map patient access grants to FHIR Consent resources
  for interoperability with external EHR systems.
