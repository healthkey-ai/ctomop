from django.db import migrations, models

ADD_DIAGNOSIS_DATE = "ALTER TABLE patient_info ADD COLUMN IF NOT EXISTS diagnosis_date DATE;"
ADD_CONDITION_STATUS = "ALTER TABLE patient_info ADD COLUMN IF NOT EXISTS condition_clinical_status VARCHAR(50);"
ADD_DISEASE_SLUG = "ALTER TABLE patient_info ADD COLUMN IF NOT EXISTS disease_slug VARCHAR(100);"
ADD_VALIDATED = "ALTER TABLE patient_info ADD COLUMN IF NOT EXISTS validated BOOLEAN;"
ADD_VALIDATED_BY = "ALTER TABLE patient_info ADD COLUMN IF NOT EXISTS validated_by VARCHAR(100);"
ADD_VALIDATION_DATE = "ALTER TABLE patient_info ADD COLUMN IF NOT EXISTS validation_date DATE;"
ADD_PHONE_NUMBER = "ALTER TABLE patient_info ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);"
ADD_FACILITY_NAME = "ALTER TABLE patient_info ADD COLUMN IF NOT EXISTS facility_name VARCHAR(255);"
ADD_PRIOR_PROCEDURES = "ALTER TABLE patient_info ADD COLUMN IF NOT EXISTS prior_procedures JSONB DEFAULT '[]'::jsonb;"

DROP_DIAGNOSIS_DATE = "ALTER TABLE patient_info DROP COLUMN IF EXISTS diagnosis_date;"
DROP_CONDITION_STATUS = "ALTER TABLE patient_info DROP COLUMN IF EXISTS condition_clinical_status;"
DROP_DISEASE_SLUG = "ALTER TABLE patient_info DROP COLUMN IF EXISTS disease_slug;"
DROP_VALIDATED = "ALTER TABLE patient_info DROP COLUMN IF EXISTS validated;"
DROP_VALIDATED_BY = "ALTER TABLE patient_info DROP COLUMN IF EXISTS validated_by;"
DROP_VALIDATION_DATE = "ALTER TABLE patient_info DROP COLUMN IF EXISTS validation_date;"
DROP_PHONE_NUMBER = "ALTER TABLE patient_info DROP COLUMN IF EXISTS phone_number;"
DROP_FACILITY_NAME = "ALTER TABLE patient_info DROP COLUMN IF EXISTS facility_name;"
DROP_PRIOR_PROCEDURES = "ALTER TABLE patient_info DROP COLUMN IF EXISTS prior_procedures;"

FORWARD_SQL = "\n".join([
    ADD_DIAGNOSIS_DATE, ADD_CONDITION_STATUS, ADD_DISEASE_SLUG,
    ADD_VALIDATED, ADD_VALIDATED_BY, ADD_VALIDATION_DATE,
    ADD_PHONE_NUMBER, ADD_FACILITY_NAME, ADD_PRIOR_PROCEDURES,
])

REVERSE_SQL = "\n".join([
    DROP_DIAGNOSIS_DATE, DROP_CONDITION_STATUS, DROP_DISEASE_SLUG,
    DROP_VALIDATED, DROP_VALIDATED_BY, DROP_VALIDATION_DATE,
    DROP_PHONE_NUMBER, DROP_FACILITY_NAME, DROP_PRIOR_PROCEDURES,
])


class Migration(migrations.Migration):
    dependencies = [("omop_core", "0044_add_clonal_bone_marrow_b_lymphocytes")]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL)],
            state_operations=[
                migrations.AddField(
                    model_name="patientinfo",
                    name="diagnosis_date",
                    field=models.DateField(blank=True, null=True, help_text="Date of initial diagnosis (from ConditionOccurrence)"),
                ),
                migrations.AddField(
                    model_name="patientinfo",
                    name="condition_clinical_status",
                    field=models.CharField(max_length=50, blank=True, null=True, help_text="Clinical status: active/remission/relapse"),
                ),
                migrations.AddField(
                    model_name="patientinfo",
                    name="disease_slug",
                    field=models.CharField(max_length=100, blank=True, null=True, help_text="Machine-readable disease ID e.g. 'multiple-myeloma'"),
                ),
                migrations.AddField(
                    model_name="patientinfo",
                    name="validated",
                    field=models.BooleanField(blank=True, null=True, help_text="Clinician validation flag"),
                ),
                migrations.AddField(
                    model_name="patientinfo",
                    name="validated_by",
                    field=models.CharField(max_length=100, blank=True, null=True, help_text="Name of clinician who validated"),
                ),
                migrations.AddField(
                    model_name="patientinfo",
                    name="validation_date",
                    field=models.DateField(blank=True, null=True, help_text="Date validated by clinician"),
                ),
                migrations.AddField(
                    model_name="patientinfo",
                    name="phone_number",
                    field=models.CharField(max_length=20, blank=True, null=True, help_text="Patient phone number"),
                ),
                migrations.AddField(
                    model_name="patientinfo",
                    name="facility_name",
                    field=models.CharField(max_length=255, blank=True, null=True, help_text="Treating institution name"),
                ),
                migrations.AddField(
                    model_name="patientinfo",
                    name="prior_procedures",
                    field=models.JSONField(blank=True, null=True, default=list, help_text="List of prior procedures from ProcedureOccurrence"),
                ),
            ],
        )
    ]
