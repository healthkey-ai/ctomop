from django.db import migrations


def seed_forward(apps, schema_editor):
    Disease = apps.get_model("omop_core", "Disease")
    CancerStage = apps.get_model("omop_core", "CancerStage")
    KarnofskyScore = apps.get_model("omop_core", "KarnofskyScore")
    EcogStatus = apps.get_model("omop_core", "EcogStatus")
    PeripheralNeuropathyGrade = apps.get_model("omop_core", "PeripheralNeuropathyGrade")
    InfectionStatus = apps.get_model("omop_core", "InfectionStatus")
    DiseaseProgression = apps.get_model("omop_core", "DiseaseProgression")
    MeasurableDisease = apps.get_model("omop_core", "MeasurableDisease")
    GelfCriteria = apps.get_model("omop_core", "GelfCriteria")
    FlipIScore = apps.get_model("omop_core", "FlipIScore")
    FollicularLymphomaGrade = apps.get_model("omop_core", "FollicularLymphomaGrade")

    # ------------------------------------------------------------------
    # Disease
    # ------------------------------------------------------------------
    for code, title in [
        ("multiple_myeloma",    "Multiple Myeloma"),
        ("follicular_lymphoma", "Follicular Lymphoma"),
        ("breast_cancer",       "Breast Cancer"),
        ("lung_cancer",         "Lung Cancer"),
        ("colorectal_cancer",   "Colorectal Cancer"),
        ("cll",                 "CLL"),
        ("other",               "Other"),
    ]:
        Disease.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # CancerStage
    # ------------------------------------------------------------------
    for code, title in [
        ("unknown",   "Unknown"),
        ("stage_i",   "Stage I"),
        ("stage_ii",  "Stage II"),
        ("stage_iii", "Stage III"),
        ("stage_iv",  "Stage IV"),
    ]:
        CancerStage.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # KarnofskyScore  (sort_key keeps numeric order; code is a string)
    # ------------------------------------------------------------------
    for sort_key, code, title in [
        (1,  "100", "100 - Normal, no complaints"),
        (2,  "90",  "90 - Normal activity, minor symptoms"),
        (3,  "80",  "80 - Normal activity with effort"),
        (4,  "70",  "70 - Cares for self, unable to work"),
        (5,  "60",  "60 - Requires occasional assistance"),
        (6,  "50",  "50 - Requires considerable assistance"),
        (7,  "40",  "40 - Disabled, special care needed"),
        (8,  "30",  "30 - Severely disabled"),
        (9,  "20",  "20 - Very sick, hospitalization needed"),
        (10, "10",  "10 - Moribund"),
        (11, "0",   "0 - Dead"),
    ]:
        KarnofskyScore.objects.get_or_create(code=code, defaults={"title": title, "sort_key": sort_key})

    # ------------------------------------------------------------------
    # EcogStatus
    # ------------------------------------------------------------------
    for code, title in [
        ("0", "0 - Fully active"),
        ("1", "1 - Restricted in physically strenuous activity"),
        ("2", "2 - Ambulatory and capable of self-care"),
        ("3", "3 - Capable of only limited self-care"),
        ("4", "4 - Completely disabled"),
        ("5", "5 - Dead"),
    ]:
        EcogStatus.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # PeripheralNeuropathyGrade
    # ------------------------------------------------------------------
    for code, title in [
        ("0", "None"),
        ("1", "Grade 1 - Mild"),
        ("2", "Grade 2 - Moderate"),
        ("3", "Grade 3 - Severe"),
        ("4", "Grade 4 - Life-threatening"),
    ]:
        PeripheralNeuropathyGrade.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # InfectionStatus
    # ------------------------------------------------------------------
    for code, title in [
        ("negative", "Negative"),
        ("positive", "Positive"),
        ("unknown",  "Unknown"),
    ]:
        InfectionStatus.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # DiseaseProgression
    # ------------------------------------------------------------------
    for code, title in [
        ("stable",      "Stable"),
        ("progressive", "Progressive"),
        ("relapsed",    "Relapsed"),
        ("refractory",  "Refractory"),
    ]:
        DiseaseProgression.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # MeasurableDisease  (IMWG criteria)
    # titles match stored PatientInfo values for backward compatibility
    # ------------------------------------------------------------------
    for code, title in [
        ("yes",     "Yes"),
        ("no",      "No"),
        ("unknown", "Unknown"),
    ]:
        MeasurableDisease.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # GelfCriteria
    # titles match stored PatientInfo values for backward compatibility
    # ------------------------------------------------------------------
    for code, title in [
        ("met",     "Met"),
        ("not_met", "Not Met"),
        ("unknown", "Unknown"),
    ]:
        GelfCriteria.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # FlipIScore
    # ------------------------------------------------------------------
    for code, title in [
        ("0", "0 - Low Risk"),
        ("1", "1 - Low Risk"),
        ("2", "2 - Intermediate Risk"),
        ("3", "3 - Intermediate Risk"),
        ("4", "4 - High Risk"),
        ("5", "5 - High Risk"),
    ]:
        FlipIScore.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # FollicularLymphomaGrade
    # ------------------------------------------------------------------
    for code, title in [
        ("grade_1",  "Grade 1"),
        ("grade_2",  "Grade 2"),
        ("grade_3a", "Grade 3a"),
        ("grade_3b", "Grade 3b"),
    ]:
        FollicularLymphomaGrade.objects.get_or_create(code=code, defaults={"title": title})


def seed_reverse(apps, schema_editor):
    for model_name in [
        "Disease", "CancerStage", "KarnofskyScore", "EcogStatus",
        "PeripheralNeuropathyGrade", "InfectionStatus", "DiseaseProgression",
        "MeasurableDisease", "GelfCriteria", "FlipIScore", "FollicularLymphomaGrade",
    ]:
        apps.get_model("omop_core", model_name).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0055_add_new_vocabulary_tables"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
