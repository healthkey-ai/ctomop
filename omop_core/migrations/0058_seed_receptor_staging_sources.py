from django.db import migrations

SOURCE_DATA = {
    "EstrogenReceptorStatus": (
        "ASCO/CAP Guideline — ER/PR Biomarker Testing in Breast Cancer",
        "https://ascopubs.org/doi/10.1200/JCO.21.01718",
    ),
    "ProgesteroneReceptorStatus": (
        "ASCO/CAP Guideline — ER/PR Biomarker Testing in Breast Cancer",
        "https://ascopubs.org/doi/10.1200/JCO.21.01718",
    ),
    "Her2Status": (
        "ASCO/CAP Guideline — HER2 Testing in Breast Cancer",
        "https://ascopubs.org/doi/10.1200/JCO.19.02105",
    ),
    "HrStatus": (
        "ASCO/CAP Guideline — ER/PR Biomarker Testing in Breast Cancer",
        "https://ascopubs.org/doi/10.1200/JCO.21.01718",
    ),
    "HrdStatus": (
        "FDA Companion Diagnostic — HRD Testing",
        "https://www.fda.gov/medical-devices/vitro-diagnostics/list-cleared-or-approved-companion-diagnostic-devices-vitro-and-imaging-tools",
    ),
    "TumorStage": (
        "TNM Classification 8th Ed. / AJCC",
        "https://www.facs.org/quality-programs/cancer-programs/american-joint-committee-on-cancer/cancer-staging-systems/",
    ),
    "NodesStage": (
        "TNM Classification 8th Ed. / AJCC",
        "https://www.facs.org/quality-programs/cancer-programs/american-joint-committee-on-cancer/cancer-staging-systems/",
    ),
    "DistantMetastasisStage": (
        "TNM Classification 8th Ed. / AJCC",
        "https://www.facs.org/quality-programs/cancer-programs/american-joint-committee-on-cancer/cancer-staging-systems/",
    ),
    "StagingModality": (
        "TNM Classification 8th Ed. / AJCC",
        "https://www.facs.org/quality-programs/cancer-programs/american-joint-committee-on-cancer/cancer-staging-systems/",
    ),
}


def seed_forward(apps, schema_editor):
    for model_name, (source_name, source_url) in SOURCE_DATA.items():
        Model = apps.get_model("omop_core", model_name)
        Model.objects.all().update(source_name=source_name, source_url=source_url)


def seed_reverse(apps, schema_editor):
    for model_name in SOURCE_DATA:
        Model = apps.get_model("omop_core", model_name)
        Model.objects.all().update(source_name=None, source_url=None)


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0057_add_vocab_source_fields"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
