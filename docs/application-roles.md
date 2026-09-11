# Application roles and access sources

PROMOP has five application roles: **staff**, **org_admin**, **doctor**,
**analyst**, and **patient**. Roles can coexist: a clinician or administrator
may also have a linked patient record. An organization/group role is scoped to
that grant; a patient membership does not grant access to other patients.

| Role | Scope |
|---|---|
| Staff | Platform administration across organizations |
| Org admin | Administration of the granting organization |
| Doctor | Clinical access within the assigned organization/group |
| Analyst | Read-only patient access within the assigned organization/group |
| Patient | Own linked patient record |

## Organization-admin trusts

Both trust types intentionally grant **org_admin** authority in the
**granting organization**:

- If Hospital A trusts Clinic B, an active professional organization-level
  grant in B confers org-admin access to A. The inherited role expires when
  its source grant expires.
- If Hospital A trusts an email domain, matching users receive org-admin
  access to A under the existing domain-trust rules.

Trusts do not confer staff or superuser status. Inheritance is one hop; it does
not recursively expand through a chain of trusts. Existing patient-only
organization membership exclusions remain in place for both trust types.
Group-only membership does not trigger organization-to-organization admin
inheritance. Removing the trust or its qualifying grant removes the inherited
role.

`get_admin_access_paths()` supplies the grant sources both to authorization
(`get_admin_orgs()`) and to role reporting. This keeps the displayed inherited
scope aligned with the authority used by organization endpoints.

## Profile API and display

`GET /api/user/` adds:

- `effective_roles`: every active role and its scope, source and expiration.
  Sources are `staff_flag`, `patient_link`, `org_grant`, `group_grant`,
  `organization_trust`, and `domain_trust`. A trust source identifies its
  source organization or email domain. Multiple sources/roles in one
  organization remain visible.
- `patient_delegations`: verified representative relationships, each naming
  the patient record and relationship. These are patient-specific delegated
  access, not a sixth organization role.

The profile displays these separately from pending invitations. The legacy
`org_accesses` list preserves organization metadata, reports each active grant,
includes inherited admin grants, and gives pending invitations `role: null`
with a separate `pending_role`. A pending invitation must not enable a
professional UI route. `access_via: explicit_grant` means a stored grant; it
must not be described as an invitation without evidence of its origin.

The existing `is_patient` and `person_id` properties remain routing hints for
patient-only mode. They are not the exhaustive role inventory: a professional
can have an active patient link even when `is_patient` is false. Clients that
need the complete picture must use `effective_roles`.

## Operational and delegated access

Django's `is_superuser` is retained for operational accounts and Django admin
permission checks. It is not an application role or mode. The supported
`create_superuser()` path requires `is_staff=True`, so its application role is
Staff. Its existing emergency-access behavior is retained.

Verified personal representation, time-limited emergency audit access,
service-token/OAuth scope grants, and premium feature entitlements retain their
separate purposes. None adds an organization role to the selector. Existing
account grants are not migrated or rewritten by this change.
