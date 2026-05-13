from django.db import migrations

# Drop tables that duplicate OMOP standard tables.
# OMOP equivalents:
#   patient_condition    → condition_occurrence
#   patient_therapy_line → episode
#   patient_medication   → drug_exposure
#   patient_procedure    → procedure_occurrence
#   patient_side_effect  → observation / condition_occurrence
#   clinical_trial_match → not needed; trial participation tracked on Episode

# Order: most-dependent first (side_effects before medication/therapy_line)
DROP_SQL = """
DROP TABLE IF EXISTS patient_side_effect;
DROP TABLE IF EXISTS patient_medication;
DROP TABLE IF EXISTS patient_therapy_line;
DROP TABLE IF EXISTS patient_condition;
DROP TABLE IF EXISTS patient_procedure;
DROP TABLE IF EXISTS clinical_trial_match;
"""

# Reverse: recreate shells only (no data recovery needed — these were never populated)
REVERSE_SQL = """
CREATE TABLE IF NOT EXISTS patient_condition (id BIGSERIAL PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS patient_therapy_line (id BIGSERIAL PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS patient_medication (id BIGSERIAL PRIMARY KEY, therapy_line_id BIGINT NOT NULL REFERENCES patient_therapy_line(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS patient_procedure (id BIGSERIAL PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS patient_side_effect (id BIGSERIAL PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS clinical_trial_match (id BIGSERIAL PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES person(person_id) ON DELETE CASCADE);
"""


class Migration(migrations.Migration):
    dependencies = [("omop_core", "0047_add_healthtree_tables")]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(sql=DROP_SQL, reverse_sql=REVERSE_SQL)],
            state_operations=[
                migrations.DeleteModel(name="PatientSideEffect"),
                migrations.DeleteModel(name="PatientMedication"),
                migrations.DeleteModel(name="PatientTherapyLine"),
                migrations.DeleteModel(name="PatientCondition"),
                migrations.DeleteModel(name="PatientProcedure"),
                migrations.DeleteModel(name="ClinicalTrialMatch"),
            ],
        )
    ]
