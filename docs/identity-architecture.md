# Identity Architecture: OIDC-Based Shared Identity

## Problem

Three services authenticate the same Firebase users independently, each creating
its own User record in its own database:

| Service | User Model | Identity Fields | Person Linkage |
|---|---|---|---|
| **ht-phr** | `AbstractUser` + custom fields | `firebase_uid`, `email`, `is_admin`, `has_medical_records` | `phr_person_id` (manual) |
| **hk-labs** | `AbstractBaseUser` (email-only) | `firebase_uid`, `email`, `identity_level`, `mfa_enabled` | `ctomop_person_id` (manual) |
| **ctomop** | Django default `User` | `username`, `email` | `PatientUser(user→User, person→Person)` + `PatientInfo.email` |

A single Firebase user (UID `abc123`) creates **three separate User rows** across
three databases. These are linked only loosely by email, and person_id bridging
requires manual admin setup.

### What's Wrong

1. **Email is mutable** — Firebase allows email changes. The ctomop Firebase
   provider looks up by email (not UID), so an email change breaks the link.
2. **Manual person_id setup** — ht-phr stores `phr_person_id`, hk-labs stores
   `ctomop_person_id`. Both require an admin to manually set the value.
3. **User data diverges** — name updated in Firebase doesn't propagate to
   hk-labs (which doesn't store names) or ctomop (which stores username at
   creation time and never updates it).
4. **No multi-provider path** — all three apps hard-code Firebase. Adding a
   corporate SAML or OIDC provider means adding similar code in three places.

---

## Design: OIDC-Based Identity

### Core Principle

The auth provider (Firebase, SAML, corporate OIDC) is the source of truth for
user identity and profile data. Each service stores only a minimal **Identity**
record: the OIDC `(issuer, sub)` tuple. No email, no name, no password.

User profile data (email, display name) is read from JWT claims at request time,
never persisted in the service's database.

### OIDC Terminology

| OIDC Claim | Meaning | Example (Firebase) |
|---|---|---|
| `iss` (issuer) | Who issued the token | `https://securetoken.google.com/healthtree-test` |
| `sub` (subject) | Immutable user ID at the issuer | `abc123def456` (Firebase UID) |
| `email` | User's email | `user@example.com` |
| `name` | Display name | `Jane Doe` |

The `(iss, sub)` pair is globally unique and immutable. It replaces
`firebase_uid` as the stable identity anchor.

### Local Provider

Not all identities come from external OIDC providers. Local identities are
stored directly in the local PostgreSQL database using Django's password
authentication. These use a synthetic issuer:

| Claim | Value |
|---|---|
| `iss` | `urn:local` |
| `sub` | `<identity.pk>` (string of the local auto-increment ID) |

This means the Identity table is the single auth model for both external
(Firebase, SAML) and local (password-based) users. Django admin login
works via standard password auth against the Identity model — no token
exchange needed.

### Deployment Modes

hk-labs and ctomop can each run in two modes:

| Mode | Auth Providers | Users | Use Case |
|---|---|---|---|
| **Federated** | Firebase + local | External users via Firebase, admins via local | Production with ht-phr host |
| **Standalone** | Local only | All users in local PostgreSQL | Development, on-prem, or single-tenant deployment |

In **standalone mode**, `PARTNER_AUTH_PROVIDERS` is empty (no external
providers configured). All users — patients, admins, service accounts —
are local identities with `iss="urn:local"`. Users sign in with
email + password through the app's own login form. The app is fully
self-contained with no Firebase or external IdP dependency.

In **federated mode**, external providers (Firebase, SAML) handle patient
and end-user authentication. Local identities are reserved for admin
users and service accounts (Django admin, management commands, API
service tokens).

The Identity model and auth flow are identical in both modes — the only
difference is which providers are listed in `PARTNER_AUTH_PROVIDERS`.
Switching from standalone to federated is a settings change, not a code
change.

```python
# Standalone mode — all users local
PARTNER_AUTH_PROVIDERS = []
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.LocalIdentityBackend",
]

# Federated mode — Firebase for end users, local for admins
PARTNER_AUTH_PROVIDERS = [
    "apps.accounts.providers.firebase.FirebaseTokenProvider",
]
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.LocalIdentityBackend",
]
```

In standalone mode, ctomop auto-provisions a Person + PatientInfo when a
local identity is created (same `_ensure_person` logic, just triggered by
local signup instead of Firebase token). hk-labs in standalone mode
resolves person_id by calling ctomop with the identity's `(urn:local, sub)`
pair — or, if ctomop is not connected, manages lab results locally
(pre-migration behavior).

---

## Identity Model

Each service stores the same minimal table:

```python
class Identity(AbstractBaseUser, PermissionsMixin):
    """Maps an OIDC subject (or local admin) to an internal ID.

    External identities (Firebase, SAML): no user data stored locally.
    Local identities (iss="urn:local"): email + password for Django admin.
    """
    issuer = models.CharField(max_length=255)
        # "https://securetoken.google.com/<project>" or "urn:local"
    sub = models.CharField(max_length=255)
        # Firebase UID, SAML subject, or str(pk) for local

    # Only populated for local (iss="urn:local") identities
    email = models.EmailField(blank=True, default="")
    name = models.CharField(max_length=255, blank=True, default="")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = IdentityManager()

    class Meta:
        db_table = "identity"
        constraints = [
            models.UniqueConstraint(
                fields=["issuer", "sub"],
                name="uq_identity_issuer_sub",
            ),
        ]

    @property
    def is_local(self) -> bool:
        return self.issuer == "urn:local"
```

`AbstractBaseUser` provides the `password` field. For **local identities**
(`iss="urn:local"`), the password is set and used for Django admin login.
For **external identities** (Firebase, SAML), the password is set to
unusable — authentication happens via token verification.

Local identities store `email` and `name` because there's no external
JWT to read them from. External identities leave these fields blank — user
data comes from `request.auth` (TokenClaims) per request.

### Request-Scoped User Data

After token verification, the auth backend attaches claims to the request:

```python
@dataclass
class TokenClaims:
    issuer: str
    sub: str
    email: str | None
    name: str | None
    raw: dict[str, Any]
```

- `request.user` → `Identity` model instance (for FK references, permissions)
- `request.auth` → `TokenClaims` (for user data)

Any view that needs the user's email reads `request.auth.email`, not a database
field.

### Authentication Flow

```
Client sends: Authorization: Bearer <JWT>
  │
  ├─ decode_jwt_unverified(token) → extract iss, sub
  │
  ├─ Route to provider based on iss:
  │    "https://securetoken.google.com/*" → FirebaseTokenProvider
  │    "https://login.corp.example.com"   → CorporateSAMLProvider (future)
  │
  ├─ Provider.verify(token) → TokenClaims(issuer, sub, email, name, raw)
  │
  ├─ Identity.objects.get_or_create(issuer=claims.issuer, sub=claims.sub)
  │
  └─ return (identity, claims)
```

No email-based lookup. No IntegrityError dance. No provider-specific fields
on the model.

---

## Per-Service Specifics

### ht-phr (Host Application)

**Role:** Frontend host. Mounts federated modules from hk-labs and ctomop.
Backend syncs Firebase custom claims and bridges to ctomop patient data.

**Current model:**
```python
class User(AbstractUser):
    firebase_uid: str
    phr_person_id: BigInteger      # manual link to ctomop Person
    identity_level: str            # ial1 / ial2
    is_admin: bool                 # from Firebase ADMIN claim
    has_medical_records: bool      # from Firebase MEDICAL_RECORDS claim
```

**Proposed:**
```python
# AUTH_USER_MODEL = "accounts.Identity"
# Identity table: (issuer, sub) only

class IdentityProfile(models.Model):
    """ht-phr-specific fields. Not shared."""
    identity = models.OneToOneField(Identity, on_delete=models.CASCADE,
                                    related_name="phr_profile")
    identity_level = models.CharField(max_length=4, default="ial1")
```

- `is_admin`, `has_medical_records` → read from `request.auth.raw` (Firebase
  custom claims are in the JWT). No local storage needed.
- `phr_person_id` → **removed**. ctomop resolves `(issuer, sub)` → Person
  internally. ht-phr never needs to know the person_id.
- `identity_level` → stays in a local profile table (app-specific concept).
- Frontend reads email/name from the auth context (Firebase SDK), not from
  the Django backend serializer.

**Frontend token injection (unchanged):**
```typescript
// All three API clients use the same Firebase ID token
client.interceptors.request.use(async (config) => {
  const token = await auth.currentUser?.getIdToken();
  config.headers.Authorization = `Bearer ${token}`;
  return config;
});
```

The host creates separate Axios instances for each backend, all carrying the
same Firebase token. Each backend validates the token independently and resolves
the identity locally.

### hk-labs (Upload Pipeline)

**Role:** Lab report upload, LLM extraction, LOINC matching, commit to ctomop.

**Current model:**
```python
class User(AbstractBaseUser, PermissionsMixin):
    email: EmailField
    firebase_uid: str
    identity_level: str
    mfa_enabled: bool
    ctomop_person_id: int          # manual link to ctomop Person
```

**Proposed:**
```python
# AUTH_USER_MODEL = "accounts.Identity"
# Identity table: (issuer, sub) only

class IdentityProfile(models.Model):
    """hk-labs-specific fields. Not shared."""
    identity = models.OneToOneField(Identity, on_delete=models.CASCADE,
                                    related_name="labs_profile")
    identity_level = models.CharField(max_length=16, default="unverified")
```

- `email` → **removed** from model. Read from `request.auth.email` (federated)
  or `request.user.email` (standalone local identity).
- `firebase_uid` → replaced by `Identity.sub` (same value, generalized).
- `mfa_enabled` → read from Firebase custom claims or token's
  `firebase.sign_in_second_factor` claim. In standalone mode, tracked in
  `IdentityProfile` or not applicable.
- `ctomop_person_id` → **removed**. On commit, hk-labs sends
  `(issuer, sub)` to ctomop. ctomop resolves to Person internally.

**Standalone mode:** All users are local (`iss="urn:local"`). Users
register and sign in with email + password. hk-labs provides its own
signup/login views backed by `LocalIdentityBackend`. When connected to
ctomop, the `(urn:local, sub)` identity is sent on commit just like any
other provider. When ctomop is not connected, hk-labs falls back to
local lab result storage (pre-migration behavior).
- `UploadJob.user` → renamed to `UploadJob.actor`, FK → Identity.

### ctomop (OMOP CDM + Lab Results)

**Role:** Clinical data storage (OMOP), lab results display, patient portal.

**Current models:**
```python
# Django default User (username, email, password, ...)
# + PatientUser(user → User, person → Person)
# + PatientInfo(person → Person, email, demographics...)
```

**Proposed:**
```python
# AUTH_USER_MODEL = "patient_portal.Identity"
# Identity table: (issuer, sub) only

class PatientUser(models.Model):
    """Links an OIDC identity to an OMOP Person."""
    identity = models.OneToOneField(Identity, on_delete=models.CASCADE,
                                    related_name="patient_user")
    person = models.OneToOneField("omop_core.Person", on_delete=models.CASCADE,
                                  related_name="portal_user")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

- `PatientUser.user` → `PatientUser.identity` (FK to Identity, not User).
- `PatientInfo.email` → **kept** as clinical contact info (part of patient
  demographics, not auth). Populated from claims on first login, updatable
  by patient. May diverge from auth email — that's OK (married name, etc.).
- `_ensure_person()` → creates `Person` + `PatientInfo` + `PatientUser` on
  first login. Uses `claims.email` for initial PatientInfo.email.
- Person ID resolution: `Identity → PatientUser → Person`.

**Standalone mode:** All users (patients, clinicians, admins) are local
identities. ctomop provides its own registration/login views. On signup,
`_ensure_person()` creates Person + PatientInfo + PatientUser linked to the
new local identity. The patient portal is fully self-contained — no
Firebase, no ht-phr host, no hk-labs dependency. hk-labs can push to
ctomop in standalone mode too (both services share the `urn:local` issuer
and resolve identities by sub).

---

## Cross-Service Flows

### Self-Service Upload (Patient Uploads Own Labs)

```
ht-phr frontend
  │ Firebase token: iss=".../healthtree-test", sub="abc123"
  │
  ├─► hk-labs backend (via labs_remote apiClient)
  │     Identity.get_or_create(iss, sub) → identity_id=7
  │     UploadJob.actor = identity_id=7
  │     ... extraction, review ...
  │
  ├─► hk-labs commit → POST to ctomop /api/lab-results/sync/
  │     Body: { "actor_iss": "...", "actor_sub": "abc123",
  │             "measurements": [...] }
  │     (no person_id — actor is uploading for self)
  │
  └─► ctomop sync endpoint:
        Identity.get_or_create(iss, sub) → identity_id=12
        PatientUser.objects.get(identity_id=12) → person_id=1042
        Create Measurements for person_id=1042
```

hk-labs never stores `ctomop_person_id`. ctomop resolves the identity
to a Person on its side.

### On-Behalf-Of Upload (Navigator Uploads for Patient)

```
ht-phr frontend
  │ Firebase token: iss=".../healthtree-test", sub="nav789" (navigator)
  │ Target patient: person_id=1042 (from ctomop patient list)
  │
  ├─► hk-labs backend
  │     Identity.get_or_create(iss, sub="nav789") → identity_id=15
  │     UploadJob.actor = identity_id=15
  │     ... extraction, review ...
  │
  ├─► hk-labs commit → POST to ctomop /api/lab-results/sync/
  │     Body: { "actor_iss": "...", "actor_sub": "nav789",
  │             "person_id": 1042,
  │             "measurements": [...] }
  │
  └─► ctomop sync endpoint:
        Validate: actor (nav789) has write access to person_id=1042
        Create Measurements for person_id=1042
        Record provenance: actor_sub="nav789"
```

The navigator's Identity exists in hk-labs (for UploadJob.actor) and
optionally in ctomop (for audit). The target patient is identified by
`person_id` — the navigator doesn't need a User record for the patient.

### Direct ctomop Read (Lab Results Display)

```
ht-phr frontend
  │ Firebase token: iss=".../healthtree-test", sub="abc123"
  │
  └─► ctomop backend (via labs_results_remote apiClient)
        Identity.get_or_create(iss, sub) → identity_id=12
        PatientUser.objects.get(identity_id=12) → person_id=1042
        Return lab results for person_id=1042
```

No ht-phr backend involvement. The frontend talks to ctomop directly
with the same Firebase token.

### Direct ctomop Edit/Delete

```
ht-phr frontend
  │ Firebase token: sub="abc123"
  │
  └─► ctomop backend
        Identity(iss, sub) → person_id=1042
        PATCH /api/lab-results/measurements/{id}/
          Validate: measurement belongs to person_id=1042
          Update measurement
```

### Standalone Mode (No ht-phr, No Firebase)

When hk-labs and/or ctomop run standalone, all flows use local identities:

```
hk-labs standalone frontend
  │ Session cookie (email + password login, iss="urn:local", sub="7")
  │
  ├─► hk-labs backend
  │     request.user = Identity(iss="urn:local", sub="7")
  │     UploadJob.actor = identity_id=7
  │     ... extraction, review ...
  │
  ├─► hk-labs commit → POST to ctomop /api/lab-results/sync/
  │     Body: { "actor_iss": "urn:local", "actor_sub": "7",
  │             "measurements": [...] }
  │
  └─► ctomop sync endpoint:
        Identity.get_or_create(iss="urn:local", sub="7")
        PatientUser → person_id=1042
        Create Measurements
```

```
ctomop standalone frontend
  │ Session cookie (email + password login, iss="urn:local", sub="12")
  │
  └─► ctomop backend
        request.user = Identity(iss="urn:local", sub="12")
        PatientUser → person_id=1042
        Return lab results / edit / delete
```

The `urn:local` issuer works the same as any external issuer in the
Identity model. The only difference is that auth is session/password-based
instead of token-based. When hk-labs pushes to ctomop, both services
must agree on the `(urn:local, sub)` mapping — either by sharing the
same database (single-DB deployment) or by ctomop accepting the sub value
from hk-labs and auto-provisioning a local identity on its side.

---

## Identity Records Across Services

### Federated Mode (Production)

Same Firebase user, three databases — but no data divergence:

```
Firebase Auth (Source of Truth)
  UID: "abc123"
  Email: "jane@example.com"
  Name: "Jane Doe"
  Custom Claims: { ADMIN: false, MEDICAL_RECORDS: true }
  iss: "https://securetoken.google.com/healthtree-test"
                         │
      ┌──────────────────┼──────────────────┐
      │                  │                  │
  ht-phr DB          hk-labs DB         ctomop DB
  ┌────────────┐    ┌────────────┐    ┌────────────┐
  │ Identity   │    │ Identity   │    │ Identity   │
  │  id: 3     │    │  id: 7     │    │  id: 12    │
  │  iss: fb…  │    │  iss: fb…  │    │  iss: fb…  │
  │  sub: abc… │    │  sub: abc… │    │  sub: abc… │
  │  email: "" │    │  email: "" │    │  email: "" │
  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘
        │                 │                 │
  ┌─────┴──────┐    ┌─────┴──────┐    ┌─────┴──────┐
  │ Identity   │    │ UploadJob  │    │PatientUser │
  │ Profile    │    │  actor ────┘    │ identity───┘
  │  ial: ial1 │    │  status    │    │ person ────┐
  └────────────┘    │  ...       │    └────────────┘
                    └────────────┘           │
                                      ┌─────┴──────┐
                                      │ Person     │
                                      │  id: 1042  │
                                      │  (OMOP)    │
                                      └────────────┘
```

External Identity rows store only `(issuer, sub)` — same values in all
three databases, nothing that can drift. The internal `id` differs per
database (auto-increment), but that's fine — it's only used for local FK
references.

### Standalone Mode (Single Service)

All users are local. No external IdP.

```
Local PostgreSQL (Source of Truth)
                         │
  hk-labs DB (standalone)          ctomop DB (standalone)
  ┌──────────────────┐             ┌──────────────────┐
  │ Identity         │             │ Identity         │
  │  id: 1           │             │  id: 1           │
  │  iss: urn:local  │             │  iss: urn:local  │
  │  sub: "1"        │             │  sub: "1"        │
  │  email: jane@…   │             │  email: jane@…   │
  │  name: Jane Doe  │             │  name: Jane Doe  │
  │  password: ••••  │             │  password: ••••  │
  └─────┬────────────┘             └─────┬────────────┘
        │                                │
  ┌─────┴──────┐                   ┌─────┴──────┐
  │ UploadJob  │                   │PatientUser │
  │  actor ────┘                   │ identity───┘
  │  status    │                   │ person ────┐
  └────────────┘                   └────────────┘
                                         │
                                   ┌─────┴──────┐
                                   │ Person     │
                                   │  id: 1042  │
                                   └────────────┘
```

Local identities store email + name + password directly. Each service
operates independently. When both run together, hk-labs sends
`(urn:local, sub)` to ctomop on commit — ctomop auto-provisions a
matching local identity if it doesn't exist yet.

---

## Adding a New Auth Provider

Adding corporate SAML (e.g., a hospital system) requires:

1. **New TokenProvider subclass** — implements `can_handle()`, `verify()`:
   ```python
   class HospitalSAMLProvider(TokenProvider):
       ISSUER = "https://login.hospital.example.com"

       def can_handle(self, token, unverified):
           return (unverified or {}).get("iss") == self.ISSUER

       def verify(self, token):
           # SAML assertion verification
           claims = verify_saml_token(token)
           return TokenClaims(
               issuer=self.ISSUER,
               sub=claims["sub"],
               email=claims.get("email"),
               name=claims.get("name"),
               raw=claims,
           )
   ```

2. **Add to `PARTNER_AUTH_PROVIDERS` setting** in whichever service(s)
   should accept this provider.

3. **Nothing else.** The Identity model, `_get_or_create`, and all
   downstream code work unchanged. A new `Identity` row is created with
   `issuer="https://login.hospital.example.com"`, `sub="hosp-user-42"`.

### Local Provider (Admin / Service Users)

Admin users authenticate via standard Django password auth against the
Identity model. No token provider is involved — Django's
`ModelBackend` handles `authenticate(email=..., password=...)`.

```python
class LocalIdentityBackend(ModelBackend):
    """Django admin login for local (urn:local) identities."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            identity = Identity.objects.get(issuer="urn:local", email=email)
        except Identity.DoesNotExist:
            return None
        if identity.check_password(password) and identity.is_active:
            return identity
        return None
```

Creating an admin user:

```python
identity = Identity.objects.create(
    issuer="urn:local",
    sub="",          # will be set to str(pk) after save
    email="admin@example.com",
    name="Admin User",
    is_staff=True,
    is_superuser=True,
)
identity.set_password("secure-password")
identity.sub = str(identity.pk)
identity.save(update_fields=["password", "sub"])
```

A management command (`createsuperuser`) would automate this.

### Multi-Provider Identity Linking

One human may authenticate via multiple providers (personal Firebase account
+ corporate SAML). These create separate Identity rows. To link them:

```python
class IdentityLink(models.Model):
    """Links multiple Identity records belonging to the same human."""
    primary = models.ForeignKey(Identity, on_delete=models.CASCADE,
                                related_name="linked_from")
    linked = models.OneToOneField(Identity, on_delete=models.CASCADE,
                                  related_name="linked_to")
    linked_at = models.DateTimeField(auto_now_add=True)
    linked_by = models.CharField(max_length=64)  # "admin", "self-service"
```

When resolving person_id, the system checks for linked identities:

```python
def resolve_person(identity):
    pu = PatientUser.objects.filter(identity=identity).first()
    if pu:
        return pu.person
    # Check linked identities
    link = IdentityLink.objects.filter(linked=identity).first()
    if link:
        return resolve_person(link.primary)
    return None
```

This is only needed when a second provider is introduced. Firebase handles
multi-provider linking internally (Google + email + phone all share one UID),
so for Firebase-only deployments, `IdentityLink` is not needed.

---

## What Stays App-Specific

The Identity model is deliberately thin. App-specific data lives in
separate tables:

| App | Local Data | Where |
|---|---|---|
| ht-phr | `identity_level` (IAL1/IAL2) | `IdentityProfile` |
| ht-phr | `is_admin`, `has_medical_records` | JWT custom claims (not stored) |
| hk-labs | `identity_level`, `mfa_enabled` | `IdentityProfile` (or JWT claims) |
| hk-labs | Upload history | `UploadJob.actor → Identity` |
| ctomop | Person link | `PatientUser.identity → Identity` |
| ctomop | Patient demographics | `PatientInfo` (clinical, not auth) |
| ctomop | Consent, messages | `PatientConsent`, `PatientMessage` via `PatientUser` |
| ctomop | Org membership | Via OAuth2 Application scoping (existing) |

---

## Migration Sequence

### Phase A: Add Identity Table (Non-Breaking)

Each service adds the `identity` table alongside the existing User model.
Existing auth continues to work.

1. Add `Identity` model and migration to each repo.
2. Add `PartnerAuthentication` variant that creates Identity records
   in parallel with existing User creation.
3. Backfill: for each existing User with `firebase_uid`, create a
   corresponding Identity row with
   `issuer="https://securetoken.google.com/<project>"`, `sub=firebase_uid`.

### Phase B: Dual-Reference FK Migration

Add Identity FK alongside existing User FK on key models. Both populated
during the transition.

**hk-labs:**
- `UploadJob`: add `actor = FK(Identity, null=True)`, keep `user` FK.
- Backfill `actor` from `user.firebase_uid` → Identity lookup.

**ctomop:**
- `PatientUser`: add `identity = FK(Identity, null=True)`, keep `user` FK.
- Backfill `identity` from User → firebase_uid → Identity lookup.

**ht-phr:**
- `IdentityProfile`: create, linked to Identity.
- Backfill `identity_level` from existing User.

### Phase C: Switch AUTH_USER_MODEL

1. Update `AUTH_USER_MODEL = "accounts.Identity"` (or equivalent).
2. Update `PartnerAuthentication` to return Identity, not User.
3. Update all views: `request.user` is now Identity, user data comes
   from `request.auth` (TokenClaims).

### Phase D: Drop Legacy User

1. Remove old User FK columns (`UploadJob.user`, `PatientUser.user`).
2. Remove old User model (hk-labs) or stop using it (ht-phr, ctomop).
3. Remove `ctomop_person_id` from hk-labs.
4. Remove `phr_person_id` from ht-phr.
5. Clean up: drop legacy `auth_user` / `accounts_user` tables.

### Phase E: Update this document with current state 
1. Remove all comparisons with old implementation
2. It should just describe current implementation 

---

## Decisions

1. **Shared package timing** — Duplicate the Identity model, TokenProvider
   base, and PartnerAuthentication across all three repos for now. Extract
   to a shared package once the interface is stable and a third-party
   consumer appears. Premature extraction adds packaging/versioning overhead
   while the API is still being shaped.

## Open Questions

1. **ServiceTokenAuthentication** — ctomop's service-to-service auth uses a
   pre-shared Bearer token mapped to a superuser. Options:
   - Keep as-is (service tokens are not user identities)
   - Create a service Identity with `iss="urn:service:hk-labs"`,
     `sub="lab-sync"`, `is_staff=True`
   - Use OAuth2 client_credentials flow (existing in ctomop)
