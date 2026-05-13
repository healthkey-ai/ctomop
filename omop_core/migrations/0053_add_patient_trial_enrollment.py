from django.db import migrations, models
import django.db.models.deletion

ADD_SQL = """
CREATE TABLE IF NOT EXISTS patient_trial_enrollment (
    id              SERIAL PRIMARY KEY,
    person_id       INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    trial_id        VARCHAR(100) NOT NULL,
    nct_id          VARCHAR(20),
    status          VARCHAR(20) NOT NULL DEFAULT 'interested',
    status_date     DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, trial_id)
);
CREATE INDEX IF NOT EXISTS patient_trial_enrollment_person_idx
    ON patient_trial_enrollment (person_id);
CREATE INDEX IF NOT EXISTS patient_trial_enrollment_trial_idx
    ON patient_trial_enrollment (trial_id);
CREATE INDEX IF NOT EXISTS patient_trial_enrollment_status_idx
    ON patient_trial_enrollment (status);
"""

DROP_SQL = "DROP TABLE IF EXISTS patient_trial_enrollment;"


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0052_seed_vocabulary_lookup_data"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=ADD_SQL, reverse_sql=DROP_SQL),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="PatientTrialEnrollment",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        (
                            "person",
                            models.ForeignKey(
                                help_text="Patient participating in the trial",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="trial_enrollments",
                                to="omop_core.person",
                            ),
                        ),
                        (
                            "trial_id",
                            models.CharField(
                                help_text="EXACT trial identifier",
                                max_length=100,
                            ),
                        ),
                        (
                            "nct_id",
                            models.CharField(
                                blank=True,
                                help_text="ClinicalTrials.gov NCT number",
                                max_length=20,
                                null=True,
                            ),
                        ),
                        (
                            "status",
                            models.CharField(
                                choices=[
                                    ("interested", "Interested"),
                                    ("registered", "Registered"),
                                    ("entered", "Entered"),
                                    ("completed", "Completed"),
                                    ("withdrawn", "Withdrawn"),
                                ],
                                default="interested",
                                help_text="Patient's current enrollment status",
                                max_length=20,
                            ),
                        ),
                        (
                            "status_date",
                            models.DateField(blank=True, null=True),
                        ),
                        (
                            "notes",
                            models.TextField(blank=True, null=True),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(auto_now_add=True),
                        ),
                        (
                            "updated_at",
                            models.DateTimeField(auto_now=True),
                        ),
                    ],
                    options={
                        "db_table": "patient_trial_enrollment",
                        "ordering": ["-status_date", "-created_at"],
                    },
                ),
                migrations.AlterUniqueTogether(
                    name="patienttrialenrollment",
                    unique_together={("person", "trial_id")},
                ),
            ],
        )
    ]
