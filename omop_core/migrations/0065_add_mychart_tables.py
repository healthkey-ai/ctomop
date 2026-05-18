from django.db import migrations, models
import django.db.models.deletion


ADD_SQL = """
CREATE TABLE IF NOT EXISTS epic_endpoint (
    id         SERIAL PRIMARY KEY,
    url        TEXT NOT NULL UNIQUE,
    name       VARCHAR(200) NOT NULL,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS epic_organization (
    id          SERIAL PRIMARY KEY,
    alias       VARCHAR(80) NOT NULL UNIQUE,
    title       VARCHAR(200) NOT NULL,
    endpoint_id INTEGER NOT NULL REFERENCES epic_endpoint(id) ON DELETE RESTRICT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS epic_organization_endpoint_idx ON epic_organization(endpoint_id);

CREATE TABLE IF NOT EXISTS oauth2_state (
    id            SERIAL PRIMARY KEY,
    state         VARCHAR(64) NOT NULL UNIQUE,
    code_verifier VARCHAR(128) NOT NULL,
    provider      VARCHAR(16) NOT NULL DEFAULT 'epic',
    user_id       INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    endpoint_id   INTEGER NOT NULL REFERENCES epic_endpoint(id) ON DELETE CASCADE,
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS oauth2_state_state_idx ON oauth2_state(state);
CREATE INDEX IF NOT EXISTS oauth2_state_user_idx ON oauth2_state(user_id);

CREATE TABLE IF NOT EXISTS fhir_token (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    endpoint_id     INTEGER NOT NULL REFERENCES epic_endpoint(id) ON DELETE RESTRICT,
    access_token    TEXT NOT NULL,
    refresh_token   TEXT NOT NULL DEFAULT '',
    id_token        TEXT NOT NULL DEFAULT '',
    expires_at      TIMESTAMPTZ NOT NULL,
    scope           TEXT NOT NULL DEFAULT '',
    fhir_patient_id VARCHAR(128) NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, endpoint_id)
);
CREATE INDEX IF NOT EXISTS fhir_token_fhir_patient_id_idx ON fhir_token(fhir_patient_id);
"""

DROP_SQL = """
DROP TABLE IF EXISTS fhir_token;
DROP TABLE IF EXISTS oauth2_state;
DROP TABLE IF EXISTS epic_organization;
DROP TABLE IF EXISTS epic_endpoint;
"""


SANDBOX_FHIR_URL = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"


def seed_self_service_org_and_sandbox(apps, schema_editor):
    Organization = apps.get_model("omop_core", "Organization")
    EpicEndpoint = apps.get_model("omop_core", "EpicEndpoint")
    EpicOrganization = apps.get_model("omop_core", "EpicOrganization")

    Organization.objects.get_or_create(
        slug="mychart-self-service",
        defaults={"name": "MyChart Self-Service"},
    )
    endpoint, _ = EpicEndpoint.objects.get_or_create(
        url=SANDBOX_FHIR_URL,
        defaults={"name": "Epic Sandbox", "is_active": True},
    )
    EpicOrganization.objects.get_or_create(
        alias="epic-sandbox",
        defaults={"title": "Epic Sandbox", "endpoint": endpoint, "is_active": True},
    )


def unseed(apps, schema_editor):
    EpicOrganization = apps.get_model("omop_core", "EpicOrganization")
    EpicEndpoint = apps.get_model("omop_core", "EpicEndpoint")
    Organization = apps.get_model("omop_core", "Organization")
    EpicOrganization.objects.filter(alias="epic-sandbox").delete()
    EpicEndpoint.objects.filter(url=SANDBOX_FHIR_URL).delete()
    Organization.objects.filter(slug="mychart-self-service").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0064_add_organization_fk_to_provenance_record"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=ADD_SQL, reverse_sql=DROP_SQL),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="EpicEndpoint",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("url", models.TextField(unique=True, help_text="FHIR R4 base URL, no trailing slash")),
                        ("name", models.CharField(max_length=200, help_text="Human-readable label, e.g., 'Epic Sandbox'")),
                        ("is_active", models.BooleanField(default=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                    ],
                    options={"db_table": "epic_endpoint"},
                ),
                migrations.CreateModel(
                    name="EpicOrganization",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("alias", models.SlugField(max_length=80, unique=True)),
                        ("title", models.CharField(max_length=200)),
                        (
                            "endpoint",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="organizations",
                                to="omop_core.epicendpoint",
                            ),
                        ),
                        ("is_active", models.BooleanField(default=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                    ],
                    options={"db_table": "epic_organization"},
                ),
                migrations.CreateModel(
                    name="OAuth2State",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("state", models.CharField(max_length=64, unique=True, db_index=True)),
                        ("code_verifier", models.CharField(max_length=128)),
                        (
                            "provider",
                            models.CharField(
                                max_length=16,
                                choices=[("epic", "Epic")],
                                default="epic",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="oauth_states",
                                to="auth.user",
                            ),
                        ),
                        (
                            "endpoint",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to="omop_core.epicendpoint",
                            ),
                        ),
                        ("metadata", models.JSONField(blank=True, default=dict)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                    ],
                    options={"db_table": "oauth2_state"},
                ),
                migrations.CreateModel(
                    name="FhirToken",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="fhir_tokens",
                                to="auth.user",
                            ),
                        ),
                        (
                            "endpoint",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="tokens",
                                to="omop_core.epicendpoint",
                            ),
                        ),
                        ("access_token", models.TextField()),
                        ("refresh_token", models.TextField(blank=True, default="")),
                        ("id_token", models.TextField(blank=True, default="")),
                        ("expires_at", models.DateTimeField()),
                        ("scope", models.TextField(blank=True, default="")),
                        ("fhir_patient_id", models.CharField(max_length=128, blank=True, default="", db_index=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "db_table": "fhir_token",
                        "unique_together": {("user", "endpoint")},
                    },
                ),
            ],
        ),
        migrations.RunPython(seed_self_service_org_and_sandbox, reverse_code=unseed),
    ]
