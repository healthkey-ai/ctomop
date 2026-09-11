from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('omop_core', '0221_seed_treatment_editor_catalogs')]

    operations = [
        # HGVS expressions and report narratives must not be truncated to 60
        # characters. This widens existing OMOP columns; no variant side table.
        migrations.AlterField(
            model_name='measurement', name='value_as_string',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='observation', name='value_as_string',
            field=models.TextField(blank=True, null=True),
        ),
    ]
