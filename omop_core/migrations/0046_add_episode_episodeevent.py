from django.db import migrations

# episode / episode_event tables are owned and created by omop_oncology.
# This migration is intentionally empty — it exists only to preserve the
# dependency chain for subsequent omop_core migrations.


class Migration(migrations.Migration):
    dependencies = [("omop_core", "0045_add_healthtree_patientinfo_fields")]
    operations = []
