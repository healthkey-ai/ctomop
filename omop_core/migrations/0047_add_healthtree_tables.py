from django.db import migrations, models
import django.db.models.deletion

CREATE_PATIENT_CONDITION = """
CREATE TABLE IF NOT EXISTS patient_condition (
    id BIGSERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    disease_slug VARCHAR(100) NOT NULL,
    snomed_code VARCHAR(50),
    icd10_code VARCHAR(20),
    clinical_status VARCHAR(20) NOT NULL DEFAULT 'active',
    onset_date DATE,
    recorded_date DATE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    validated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_PATIENT_THERAPY_LINE = """
CREATE TABLE IF NOT EXISTS patient_therapy_line (
    id BIGSERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    disease_slug VARCHAR(100) NOT NULL,
    line_number INTEGER NOT NULL,
    phase VARCHAR(20),
    start_date DATE,
    end_date DATE,
    outcome VARCHAR(10),
    is_clinical_trial BOOLEAN NOT NULL DEFAULT FALSE,
    clinical_trial_nct_id VARCHAR(20),
    discontinuation_reason VARCHAR(100),
    intent VARCHAR(50),
    ongoing BOOLEAN NOT NULL DEFAULT FALSE,
    validated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_PATIENT_MEDICATION = """
CREATE TABLE IF NOT EXISTS patient_medication (
    id BIGSERIAL PRIMARY KEY,
    therapy_line_id BIGINT NOT NULL REFERENCES patient_therapy_line(id) ON DELETE CASCADE,
    drug_name VARCHAR(255) NOT NULL,
    rxnorm_code VARCHAR(50),
    dose_value NUMERIC(10,3),
    dose_unit VARCHAR(50),
    frequency VARCHAR(100),
    route VARCHAR(100),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_PATIENT_PROCEDURE = """
CREATE TABLE IF NOT EXISTS patient_procedure (
    id BIGSERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    procedure_name VARCHAR(255) NOT NULL,
    cpt_code VARCHAR(20),
    performed_date DATE,
    validated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_PATIENT_DOCUMENT = """
CREATE TABLE IF NOT EXISTS patient_document (
    id BIGSERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    doc_type VARCHAR(50) NOT NULL,
    title VARCHAR(255),
    file_url TEXT,
    file_name VARCHAR(255),
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_PATIENT_SIDE_EFFECT = """
CREATE TABLE IF NOT EXISTS patient_side_effect (
    id BIGSERIAL PRIMARY KEY,
    therapy_line_id BIGINT REFERENCES patient_therapy_line(id) ON DELETE CASCADE,
    medication_id BIGINT REFERENCES patient_medication(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    effect_name VARCHAR(255) NOT NULL,
    severity INTEGER NOT NULL DEFAULT 0,
    onset_date DATE,
    resolution_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_CLINICAL_TRIAL_MATCH = """
CREATE TABLE IF NOT EXISTS clinical_trial_match (
    id BIGSERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    nct_id VARCHAR(20) NOT NULL,
    logical_match BOOLEAN NOT NULL,
    matched_rules INTEGER NOT NULL DEFAULT 0,
    failed_rules INTEGER NOT NULL DEFAULT 0,
    ignored_rules INTEGER NOT NULL DEFAULT 0,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, nct_id)
);
"""

FORWARD_SQL = "\n".join([
    CREATE_PATIENT_CONDITION,
    CREATE_PATIENT_THERAPY_LINE,
    CREATE_PATIENT_MEDICATION,
    CREATE_PATIENT_PROCEDURE,
    CREATE_PATIENT_DOCUMENT,
    CREATE_PATIENT_SIDE_EFFECT,
    CREATE_CLINICAL_TRIAL_MATCH,
])

REVERSE_SQL = """
DROP TABLE IF EXISTS clinical_trial_match;
DROP TABLE IF EXISTS patient_side_effect;
DROP TABLE IF EXISTS patient_document;
DROP TABLE IF EXISTS patient_procedure;
DROP TABLE IF EXISTS patient_medication;
DROP TABLE IF EXISTS patient_therapy_line;
DROP TABLE IF EXISTS patient_condition;
"""


class Migration(migrations.Migration):
    dependencies = [("omop_core", "0046_add_episode_episodeevent")]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL)],
            state_operations=[
                migrations.CreateModel(
                    name="PatientCondition",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("person", models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="conditions",
                            to="omop_core.person",
                        )),
                        ("disease_slug", models.CharField(max_length=100, help_text="e.g. 'multiple-myeloma'")),
                        ("snomed_code", models.CharField(max_length=50, blank=True, null=True)),
                        ("icd10_code", models.CharField(max_length=20, blank=True, null=True)),
                        ("clinical_status", models.CharField(
                            max_length=20, default="active",
                            choices=[
                                ("active", "Active"), ("recurrence", "Recurrence"),
                                ("relapse", "Relapse"), ("remission", "Remission"),
                                ("resolved", "Resolved"), ("inactive", "Inactive"),
                            ],
                        )),
                        ("onset_date", models.DateField(blank=True, null=True)),
                        ("recorded_date", models.DateField(blank=True, null=True)),
                        ("is_primary", models.BooleanField(default=False)),
                        ("validated", models.BooleanField(default=False)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                    ],
                    options={"db_table": "patient_condition"},
                ),
                migrations.CreateModel(
                    name="PatientTherapyLine",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("person", models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="therapy_lines",
                            to="omop_core.person",
                        )),
                        ("disease_slug", models.CharField(max_length=100)),
                        ("line_number", models.IntegerField(help_text="1, 2, 3…")),
                        ("phase", models.CharField(
                            max_length=20, blank=True, null=True,
                            choices=[
                                ("induction", "Induction"), ("intermediate", "Intermediate"),
                                ("consolidation", "Consolidation"), ("maintenance", "Maintenance"),
                            ],
                        )),
                        ("start_date", models.DateField(blank=True, null=True)),
                        ("end_date", models.DateField(blank=True, null=True)),
                        ("outcome", models.CharField(
                            max_length=10, blank=True, null=True,
                            choices=[
                                ("CR", "Complete Response"), ("sCR", "Stringent Complete Response"),
                                ("VGPR", "Very Good Partial Response"), ("PR", "Partial Response"),
                                ("MR", "Minor Response"), ("SD", "Stable Disease"),
                                ("PD", "Progressive Disease"), ("NA", "N/A"),
                            ],
                        )),
                        ("is_clinical_trial", models.BooleanField(default=False)),
                        ("clinical_trial_nct_id", models.CharField(max_length=20, blank=True, null=True)),
                        ("discontinuation_reason", models.CharField(max_length=100, blank=True, null=True)),
                        ("intent", models.CharField(max_length=50, blank=True, null=True)),
                        ("ongoing", models.BooleanField(default=False)),
                        ("validated", models.BooleanField(default=False)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                    ],
                    options={"db_table": "patient_therapy_line", "ordering": ["line_number"]},
                ),
                migrations.CreateModel(
                    name="PatientMedication",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("therapy_line", models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="medications",
                            to="omop_core.patienttherapyline",
                        )),
                        ("drug_name", models.CharField(max_length=255)),
                        ("rxnorm_code", models.CharField(max_length=50, blank=True, null=True)),
                        ("dose_value", models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)),
                        ("dose_unit", models.CharField(max_length=50, blank=True, null=True)),
                        ("frequency", models.CharField(max_length=100, blank=True, null=True)),
                        ("route", models.CharField(max_length=100, blank=True, null=True)),
                        ("start_date", models.DateField(blank=True, null=True)),
                        ("end_date", models.DateField(blank=True, null=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                    ],
                    options={"db_table": "patient_medication"},
                ),
                migrations.CreateModel(
                    name="PatientProcedure",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("person", models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="patient_procedures",
                            to="omop_core.person",
                        )),
                        ("procedure_name", models.CharField(max_length=255)),
                        ("cpt_code", models.CharField(max_length=20, blank=True, null=True)),
                        ("performed_date", models.DateField(blank=True, null=True)),
                        ("validated", models.BooleanField(default=False)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                    ],
                    options={"db_table": "patient_procedure"},
                ),
                migrations.CreateModel(
                    name="PatientDocument",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("person", models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="documents",
                            to="omop_core.person",
                        )),
                        ("doc_type", models.CharField(
                            max_length=50,
                            choices=[
                                ("FISH", "FISH"), ("GEP", "GEP"), ("NGS", "NGS"),
                                ("CYTOMETRY", "Flow Cytometry"), ("CYTOGENETICS", "Cytogenetics"),
                                ("LAB_RESULTS", "Lab Results"),
                                ("FULL_MEDICAL_RECORDS", "Full Medical Records"),
                                ("MRD", "MRD"), ("BONE_MARROW", "Bone Marrow"),
                                ("CONSENT", "Consent"), ("IMAGING", "Imaging"), ("OTHER", "Other"),
                            ],
                        )),
                        ("title", models.CharField(max_length=255, blank=True, null=True)),
                        ("file_url", models.URLField(blank=True, null=True)),
                        ("file_name", models.CharField(max_length=255, blank=True, null=True)),
                        ("verified", models.BooleanField(default=False)),
                        ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                    ],
                    options={"db_table": "patient_document"},
                ),
                migrations.CreateModel(
                    name="PatientSideEffect",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("therapy_line", models.ForeignKey(
                            blank=True, null=True,
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="side_effects",
                            to="omop_core.patienttherapyline",
                        )),
                        ("medication", models.ForeignKey(
                            blank=True, null=True,
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="side_effects",
                            to="omop_core.patientmedication",
                        )),
                        ("person", models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="side_effects",
                            to="omop_core.person",
                        )),
                        ("effect_name", models.CharField(max_length=255)),
                        ("severity", models.IntegerField(
                            default=0, help_text="CTCAE grade 0–5",
                            choices=[(0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
                        )),
                        ("onset_date", models.DateField(blank=True, null=True)),
                        ("resolution_date", models.DateField(blank=True, null=True)),
                        ("notes", models.TextField(blank=True, null=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                    ],
                    options={"db_table": "patient_side_effect"},
                ),
                migrations.CreateModel(
                    name="ClinicalTrialMatch",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("person", models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="trial_matches",
                            to="omop_core.person",
                        )),
                        ("nct_id", models.CharField(max_length=20)),
                        ("logical_match", models.BooleanField()),
                        ("matched_rules", models.IntegerField(default=0)),
                        ("failed_rules", models.IntegerField(default=0)),
                        ("ignored_rules", models.IntegerField(default=0)),
                        ("computed_at", models.DateTimeField(auto_now_add=True)),
                    ],
                    options={
                        "db_table": "clinical_trial_match",
                        "unique_together": {("person", "nct_id")},
                    },
                ),
            ],
        )
    ]
