from django.db import migrations, models

ALTER_SQL = "ALTER TABLE drug_exposure ALTER COLUMN drug_exposure_end_date DROP NOT NULL;"
REVERT_SQL = "ALTER TABLE drug_exposure ALTER COLUMN drug_exposure_end_date SET NOT NULL;"


class Migration(migrations.Migration):
    dependencies = [("omop_core", "0048_remove_non_omop_tables")]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(sql=ALTER_SQL, reverse_sql=REVERT_SQL)],
            state_operations=[
                migrations.AlterField(
                    model_name="drugexposure",
                    name="drug_exposure_end_date",
                    field=models.DateField(null=True, blank=True),
                )
            ],
        )
    ]
