from django.db import migrations, models

# ---------------------------------------------------------------------------
# All vocabulary tables that need source_name / source_url columns
# ---------------------------------------------------------------------------
VOCAB_TABLES = [
    "vocabulary_ethnicity",
    "vocabulary_stem_cell_transplant",
    "vocabulary_histologic_type",
    "vocabulary_estrogen_receptor_status",
    "vocabulary_progesterone_receptor_status",
    "vocabulary_her2_status",
    "vocabulary_hr_status",
    "vocabulary_hrd_status",
    "vocabulary_mutation_origin",
    "vocabulary_mutation_gene",
    "vocabulary_mutation_interpretation",
    "vocabulary_mutation_code",
    "vocabulary_tumor_stage",
    "vocabulary_nodes_stage",
    "vocabulary_distant_metastasis_stage",
    "vocabulary_staging_modality",
    "vocabulary_toxicity_grade",
    "vocabulary_language",
    "vocabulary_language_skill_level",
    "vocabulary_binet_stage",
    "vocabulary_protein_expression",
    "vocabulary_richter_transformation",
    "vocabulary_tumor_burden",
    "vocabulary_morphologic_variant",
    "vocabulary_disease_activity",
    "vocabulary_pre_existing_condition_category",
    "vocabulary_disease",
    "vocabulary_cancer_stage",
    "vocabulary_karnofsky_score",
    "vocabulary_ecog_status",
    "vocabulary_peripheral_neuropathy_grade",
    "vocabulary_infection_status",
    "vocabulary_disease_progression",
    "vocabulary_measurable_disease",
    "vocabulary_gelf_criteria",
    "vocabulary_flipi_score",
    "vocabulary_follicular_lymphoma_grade",
]

ADD_SQLS = []
DROP_SQLS = []
for t in VOCAB_TABLES:
    ADD_SQLS.append(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS source_name TEXT;")
    ADD_SQLS.append(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS source_url TEXT;")
    DROP_SQLS.append(f"ALTER TABLE {t} DROP COLUMN IF EXISTS source_name;")
    DROP_SQLS.append(f"ALTER TABLE {t} DROP COLUMN IF EXISTS source_url;")


# ---------------------------------------------------------------------------
# Source metadata — keyed by model name as used by apps.get_model()
# ---------------------------------------------------------------------------
SOURCE_DATA = {
    "EcogStatus": (
        "ECOG Performance Status Scale, LOINC 89262-0",
        "https://ecog-acrin.org/resources/ecog-performance-status/",
    ),
    "KarnofskyScore": (
        "Karnofsky Performance Score, LOINC 89243-0",
        "https://loinc.org/89243-0",
    ),
    "PeripheralNeuropathyGrade": (
        "CTCAE v6.0 — Peripheral Motor Neuropathy",
        "https://dctd.cancer.gov/research/ctep-trials/for-sites/adverse-events",
    ),
    "ToxicityGrade": (
        "CTCAE v6.0 — General Adverse Events",
        "https://dctd.cancer.gov/research/ctep-trials/for-sites/adverse-events",
    ),
    "Disease": (
        "NCI Thesaurus (NCIt)",
        "https://ncit.nci.nih.gov/ncitbrowser/",
    ),
    "CancerStage": (
        "TNM Classification 8th Ed. / AJCC",
        "https://www.facs.org/quality-programs/cancer-programs/american-joint-committee-on-cancer/cancer-staging-systems/",
    ),
    "InfectionStatus": (
        "SNOMED CT",
        "https://browser.ihtsdotools.org/",
    ),
    "DiseaseProgression": (
        "IMWG Consensus Criteria",
        "https://www.myeloma.org/imwg-publications",
    ),
    "MeasurableDisease": (
        "IMWG Uniform Response Criteria",
        "https://www.myeloma.org/resource-library/international-myeloma-working-group-imwg-uniform-response-criteria-multiple",
    ),
    "GelfCriteria": (
        "GELF Criteria for High Tumor Burden",
        "https://www.mdcalc.com/calc/2321/groupe-detude-des-lymphomes-folliculaires-gelf-criteria",
    ),
    "FlipIScore": (
        "FLIPI (Solal-Celigny et al. 2004)",
        "https://ashpublications.org/blood/article/104/5/1258/18907/Follicular-Lymphoma-International-Prognostic-Index",
    ),
    "FollicularLymphomaGrade": (
        "WHO Classification of Haematolymphoid Tumours (2022)",
        "https://www.who.int/publications/i/item/9789240093706",
    ),
    "Ethnicity": (
        "HL7 v3 Race and Ethnicity Code System",
        "https://terminology.hl7.org/CodeSystem-v3-Ethnicity.html",
    ),
    "PreExistingConditionCategory": (
        "SNOMED CT / ICD-10-CM",
        "https://browser.ihtsdotools.org/",
    ),
}

# NCIt code updates for Disease vocabulary
DISEASE_CODE_MAP = {
    "Multiple Myeloma":    "C3242",
    "Follicular Lymphoma": "C3209",
    "Breast Cancer":       "C9335",
    "Lung Cancer":         "C4872",
    "Colorectal Cancer":   "C5105",
    "CLL":                 "C2987",
    "Other":               "other",
}

# NCIt code updates for CancerStage vocabulary
CANCER_STAGE_CODE_MAP = {
    "Stage I":   "C27966",
    "Stage II":  "C28054",
    "Stage III": "C27970",
    "Stage IV":  "C27971",
    "Unknown":   "C17998",
}

# SNOMED CT code updates for InfectionStatus vocabulary
INFECTION_STATUS_CODE_MAP = {
    "Negative": "260385009",
    "Positive": "10828004",
    "Unknown":  "261665006",
}


def populate_sources(apps, schema_editor):
    for model_name, (source_name, source_url) in SOURCE_DATA.items():
        try:
            Model = apps.get_model("omop_core", model_name)
            Model.objects.all().update(source_name=source_name, source_url=source_url)
        except LookupError:
            pass  # model not registered in this migration state

    # Update Disease codes to NCIt
    Disease = apps.get_model("omop_core", "Disease")
    for title, new_code in DISEASE_CODE_MAP.items():
        Disease.objects.filter(title=title).update(code=new_code)

    # Update CancerStage codes to NCIt
    CancerStage = apps.get_model("omop_core", "CancerStage")
    for title, new_code in CANCER_STAGE_CODE_MAP.items():
        CancerStage.objects.filter(title=title).update(code=new_code)

    # Update InfectionStatus codes to SNOMED CT
    InfectionStatus = apps.get_model("omop_core", "InfectionStatus")
    for title, new_code in INFECTION_STATUS_CODE_MAP.items():
        InfectionStatus.objects.filter(title=title).update(code=new_code)


def depopulate_sources(apps, schema_editor):
    # Reverse source_name/source_url (set to NULL) — code reversals below
    for model_name in SOURCE_DATA:
        try:
            Model = apps.get_model("omop_core", model_name)
            Model.objects.all().update(source_name=None, source_url=None)
        except LookupError:
            pass

    # Reverse Disease codes
    Disease = apps.get_model("omop_core", "Disease")
    reverse_disease = {v: k for k, v in DISEASE_CODE_MAP.items() if v != "other"}
    for new_code, title in reverse_disease.items():
        Disease.objects.filter(title=title).update(code=new_code.lower().replace(" ", "_"))

    # Reverse CancerStage codes
    CancerStage = apps.get_model("omop_core", "CancerStage")
    reverse_stage = {
        "C27966": "stage_i",
        "C28054": "stage_ii",
        "C27970": "stage_iii",
        "C27971": "stage_iv",
        "C17998": "unknown",
    }
    for new_code, old_code in reverse_stage.items():
        CancerStage.objects.filter(code=new_code).update(code=old_code)

    # Reverse InfectionStatus codes
    InfectionStatus = apps.get_model("omop_core", "InfectionStatus")
    reverse_infection = {v: k.lower() for k, v in INFECTION_STATUS_CODE_MAP.items()}
    for new_code, old_code in reverse_infection.items():
        InfectionStatus.objects.filter(code=new_code).update(code=old_code)


# ---------------------------------------------------------------------------
# State operations: AddField for every concrete vocabulary model
# ---------------------------------------------------------------------------
_SOURCE_FIELDS = [
    ("source_name", models.TextField(blank=True, null=True)),
    ("source_url",  models.TextField(blank=True, null=True)),
]

_VOCAB_MODELS = [
    "Ethnicity", "StemCellTransplant", "HistologicType",
    "EstrogenReceptorStatus", "ProgesteroneReceptorStatus", "Her2Status",
    "HrStatus", "HrdStatus", "MutationOrigin", "MutationGene",
    "MutationInterpretation", "MutationCode", "TumorStage", "NodesStage",
    "DistantMetastasisStage", "StagingModality", "ToxicityGrade",
    "Language", "LanguageSkillLevel", "BinetStage", "ProteinExpression",
    "RichterTransformation", "TumorBurden", "MorphologicVariant",
    "DiseaseActivity", "PreExistingConditionCategory",
    "Disease", "CancerStage", "KarnofskyScore", "EcogStatus",
    "PeripheralNeuropathyGrade", "InfectionStatus", "DiseaseProgression",
    "MeasurableDisease", "GelfCriteria", "FlipIScore", "FollicularLymphomaGrade",
]

_state_add_ops = []
for model_name in _VOCAB_MODELS:
    for field_name, field in _SOURCE_FIELDS:
        _state_add_ops.append(
            migrations.AddField(
                model_name=model_name,
                name=field_name,
                field=field,
            )
        )


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0056_seed_new_vocabulary_data"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=sql, reverse_sql=drop)
                for sql, drop in zip(ADD_SQLS, DROP_SQLS)
            ],
            state_operations=_state_add_ops,
        ),
        migrations.RunPython(populate_sources, depopulate_sources),
    ]
