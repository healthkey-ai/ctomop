from django.db import migrations, models
import django.db.models.deletion

ADD_SQL = """
CREATE TABLE IF NOT EXISTS organization (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    slug        VARCHAR(60)  NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS application_organization (
    id              SERIAL  PRIMARY KEY,
    application_id  INTEGER NOT NULL UNIQUE REFERENCES oauth2_provider_application(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE
);

ALTER TABLE patient_info
    ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organization(id) ON DELETE SET NULL;
"""

DROP_SQL = """
ALTER TABLE patient_info DROP COLUMN IF EXISTS organization_id;
DROP TABLE IF EXISTS application_organization;
DROP TABLE IF EXISTS organization;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0060_remove_breastcancerfirstlinetherapy_sort_key_and_more"),
        ("oauth2_provider", "0010_application_allowed_origins"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=ADD_SQL, reverse_sql=DROP_SQL),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="Organization",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("slug", models.SlugField(max_length=60, unique=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                    ],
                    options={"db_table": "organization"},
                ),
                migrations.CreateModel(
                    name="ApplicationOrganization",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "application",
                            models.OneToOneField(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="org_profile",
                                to="oauth2_provider.application",
                            ),
                        ),
                        (
                            "organization",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="applications",
                                to="omop_core.organization",
                            ),
                        ),
                    ],
                    options={"db_table": "application_organization"},
                ),
                migrations.AddField(
                    model_name="patientinfo",
                    name="organization",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="patients",
                        to="omop_core.organization",
                        help_text="Owning organization — scopes API access for service clients",
                    ),
                ),
            ],
        )
    ]
