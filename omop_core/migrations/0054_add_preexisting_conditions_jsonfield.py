from django.db import migrations, models

ADD_SQL = "ALTER TABLE patient_info ADD COLUMN IF NOT EXISTS preexisting_conditions JSONB DEFAULT '[]'::jsonb;"
DROP_SQL = "ALTER TABLE patient_info DROP COLUMN IF EXISTS preexisting_conditions;"


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0053_add_patient_trial_enrollment"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=ADD_SQL, reverse_sql=DROP_SQL),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="patientinfo",
                    name="preexisting_conditions",
                    field=models.JSONField(
                        blank=True,
                        null=True,
                        default=list,
                        help_text="List of pre-existing condition categories from PreExistingConditionCategory vocabulary",
                    ),
                )
            ],
        )
    ]
