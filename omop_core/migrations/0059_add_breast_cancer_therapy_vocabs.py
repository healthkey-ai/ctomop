from django.db import migrations, models

ADD_SQLS = [
    """CREATE TABLE IF NOT EXISTS vocabulary_breast_cancer_first_line_therapy (
        id SERIAL PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL UNIQUE,
        llm_hint TEXT,
        sort_key INTEGER,
        source_name TEXT,
        source_url TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS vocabulary_breast_cancer_second_line_therapy (
        id SERIAL PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL UNIQUE,
        llm_hint TEXT,
        sort_key INTEGER,
        source_name TEXT,
        source_url TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS vocabulary_breast_cancer_later_line_therapy (
        id SERIAL PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL UNIQUE,
        llm_hint TEXT,
        sort_key INTEGER,
        source_name TEXT,
        source_url TEXT
    );""",
]

DROP_SQLS = [
    "DROP TABLE IF EXISTS vocabulary_breast_cancer_first_line_therapy;",
    "DROP TABLE IF EXISTS vocabulary_breast_cancer_second_line_therapy;",
    "DROP TABLE IF EXISTS vocabulary_breast_cancer_later_line_therapy;",
]

_BASE_FIELDS = [
    ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
    ("code", models.TextField(db_index=True, unique=True)),
    ("title", models.TextField(db_index=True, unique=True)),
    ("llm_hint", models.TextField(blank=True, null=True)),
    ("sort_key", models.IntegerField(blank=True, null=True)),
    ("source_name", models.TextField(blank=True, null=True)),
    ("source_url", models.TextField(blank=True, null=True)),
]

NCCN_SOURCE = (
    "NCCN Clinical Practice Guidelines in Oncology — Breast Cancer",
    "https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1419",
)

FIRST_LINE_THERAPIES = [
    (10,  "watchful_waiting",           "Watchful Waiting (Active Surveillance)"),
    (20,  "lumpectomy",                 "Lumpectomy (Lumpectomy)"),
    (30,  "mastectomy",                 "Mastectomy (Mastectomy)"),
    (40,  "aromatase_inhibitor",        "Aromatase Inhibitor (Aromatase Inhibitor)"),
    (50,  "trastuzumab",                "Trastuzumab (Herceptin) (Trastuzumab)"),
    (60,  "pertuzumab",                 "Pertuzumab (Perjeta) (Pertuzumab)"),
    (70,  "genomic_testing",            "Genomic Testing (Genomic Testing)"),
    (80,  "tamoxifen",                  "Tamoxifen (Tamoxifen)"),
    (90,  "letrozole",                  "Letrozole (Letrozole)"),
    (100, "anastrozole",                "Anastrozole (Arimidex) (Anastrozole)"),
    (110, "exemestane",                 "Exemestane (Exemestane)"),
    (120, "lumpectomy_radiation",       "Lumpectomy + Radiation (Lumpectomy, Ipsilateral Breast Radiation, Adjuvant Radiotherapy)"),
    (130, "mastectomy_radiation",       "Mastectomy + Radiation (Mastectomy, Ipsilateral Breast Radiation, Adjuvant Radiotherapy)"),
    (140, "alnd_lumpectomy_radiation",  "Axillary LND + Lumpectomy + Radiation (Lumpectomy, Axillary Lymph Node Dissection (ALND), Ipsilateral Breast Radiation, Adjuvant Radiotherapy)"),
    (150, "alnd_mastectomy",            "Axillary LND + Mastectomy (Mastectomy, Axillary Lymph Node Dissection (ALND))"),
    (160, "alnd_mastectomy_radiation",  "Axillary LND + Mastectomy + Radiation (Mastectomy, Axillary Lymph Node Dissection (ALND), Ipsilateral Breast Radiation, Adjuvant Radiotherapy)"),
]

SECOND_LINE_THERAPIES = [
    (10,  "fulvestrant",                "Fulvestrant (Faslodex) (Fulvestrant)"),
    (20,  "exemestane_everolimus",      "Exemestane + Everolimus (Exemestane, Everolimus)"),
    (30,  "atezolizumab",               "Atezolizumab (Atezolizumab)"),
    (40,  "sacituzumab_govitecan",      "Sacituzumab Govitecan (Sacituzumab Govitecan)"),
    (50,  "platinum_chemo",             "Platinum-Based Chemotherapy (Platinum-Based Chemotherapy)"),
    (60,  "parp_inhibitor",             "PARP Inhibitor (PARP Inhibitor)"),
    (70,  "other_chemo",                "Other Chemotherapy (Other Chemotherapy)"),
    (80,  "capivasertib",               "Capivasertib (Capivasertib)"),
    (90,  "alnd_lumpectomy_radiation",  "Axillary LND + Lumpectomy + Radiation (Lumpectomy, Axillary Lymph Node Dissection (ALND), Ipsilateral Breast Radiation, Adjuvant Radiotherapy)"),
    (100, "alnd_mastectomy",            "Axillary LND + Mastectomy (Mastectomy, Axillary Lymph Node Dissection (ALND))"),
    (110, "alnd_mastectomy_radiation",  "Axillary LND + Mastectomy + Radiation (Mastectomy, Axillary Lymph Node Dissection (ALND), Ipsilateral Breast Radiation, Adjuvant Radiotherapy)"),
]

LATER_LINE_THERAPIES = [
    (10,  "fulvestrant",                    "Fulvestrant (Faslodex) (Fulvestrant)"),
    (20,  "exemestane_everolimus",          "Exemestane + Everolimus (Exemestane, Everolimus)"),
    (30,  "sacituzumab_govitecan",          "Sacituzumab Govitecan (Sacituzumab Govitecan)"),
    (40,  "alpelisib_fulvestrant",          "Alpelisib + Fulvestrant (Alpelisib, Fulvestrant)"),
    (50,  "capivasertib_fulvestrant",       "Capivasertib + Fulvestrant (Fulvestrant, Capivasertib)"),
    (60,  "elacestrant",                    "Elacestrant (Elacestrant)"),
    (70,  "tamoxifen",                      "Tamoxifen (Tamoxifen)"),
    (80,  "megestrol_acetate",              "Megestrol acetate (Megestrol acetate)"),
    (90,  "capecitabine",                   "Capecitabine (Capecitabine)"),
    (100, "eribulin",                       "Eribulin (Eribulin)"),
    (110, "vinorelbine",                    "Vinorelbine (Vinorelbine)"),
    (120, "gemcitabine",                    "Gemcitabine (Gemcitabine)"),
    (130, "paclitaxel",                     "Paclitaxel (Paclitaxel)"),
    (140, "docetaxel",                      "Docetaxel (Docetaxel)"),
    (150, "trastuzumab_deruxtecan",         "Trastuzumab deruxtecan (T-DXd / Enhertu) (Trastuzumab Deruxtecan)"),
    (160, "tucatinib_trastuzumab_cape",     "Tucatinib + Trastuzumab + Capecitabine (Trastuzumab, Capecitabine, Tucatinib)"),
    (170, "lapatinib",                      "Lapatinib (Tykerb) (Lapatinib)"),
    (180, "neratinib",                      "Neratinib (Nerlynx) (Neratinib)"),
    (190, "trastuzumab_emtansine",          "Trastuzumab emtansine (T-DM1 / Kadcyla) (Trastuzumab Emtansine)"),
    (200, "atezolizumab_nab_paclitaxel",    "Atezolizumab + Nab-Paclitaxel (Atezolizumab, Nab-Paclitaxel)"),
    (210, "pembrolizumab_chemo",            "Pembrolizumab + Chemotherapy (Pembrolizumab)"),
    (220, "olaparib",                       "Olaparib (Olaparib)"),
    (230, "talazoparib",                    "Talazoparib (Talazoparib)"),
    (240, "carboplatin",                    "Carboplatin (Carboplatin)"),
    (250, "cisplatin",                      "Cisplatin (Cisplatin)"),
    (260, "alpelisib_monotherapy",          "Alpelisib (Piqray) Monotherapy (Alpelisib)"),
    (270, "capivasertib",                   "Capivasertib (Capivasertib)"),
    (280, "larotrectinib",                  "Larotrectinib (Larotrectinib)"),
    (290, "entrectinib",                    "Entrectinib (Entrectinib)"),
    (300, "liposomal_doxorubicin",          "Liposomal Doxorubicin (Doxorubicin)"),
    (310, "alnd_radiation",                 "Axillary LND + Radiation (Axillary Lymph Node Dissection (ALND), Ipsilateral Breast Radiation)"),
    (320, "alnd_mastectomy",                "Axillary LND + Mastectomy (Mastectomy, Axillary Lymph Node Dissection (ALND))"),
    (330, "alnd_mastectomy_radiation",      "Axillary LND + Mastectomy + Radiation (Mastectomy, Axillary Lymph Node Dissection (ALND), Ipsilateral Breast Radiation, Adjuvant Radiotherapy)"),
]


def seed_forward(apps, schema_editor):
    source_name, source_url = NCCN_SOURCE

    FirstLine = apps.get_model("omop_core", "BreastCancerFirstLineTherapy")
    for sort_key, code, title in FIRST_LINE_THERAPIES:
        FirstLine.objects.get_or_create(
            code=code,
            defaults={"title": title, "sort_key": sort_key, "source_name": source_name, "source_url": source_url},
        )

    SecondLine = apps.get_model("omop_core", "BreastCancerSecondLineTherapy")
    for sort_key, code, title in SECOND_LINE_THERAPIES:
        SecondLine.objects.get_or_create(
            code=code,
            defaults={"title": title, "sort_key": sort_key, "source_name": source_name, "source_url": source_url},
        )

    LaterLine = apps.get_model("omop_core", "BreastCancerLaterLineTherapy")
    for sort_key, code, title in LATER_LINE_THERAPIES:
        LaterLine.objects.get_or_create(
            code=code,
            defaults={"title": title, "sort_key": sort_key, "source_name": source_name, "source_url": source_url},
        )

    # Populate source for HistologicType (columns exist from 0057 but were not seeded)
    HistologicType = apps.get_model("omop_core", "HistologicType")
    HistologicType.objects.all().update(
        source_name="WHO Classification of Tumours of the Breast (5th Ed.) / ICD-O-3",
        source_url="https://www.iarc.fr/cards_page/who-classification-of-tumours/",
    )


def seed_reverse(apps, schema_editor):
    apps.get_model("omop_core", "BreastCancerFirstLineTherapy").objects.all().delete()
    apps.get_model("omop_core", "BreastCancerSecondLineTherapy").objects.all().delete()
    apps.get_model("omop_core", "BreastCancerLaterLineTherapy").objects.all().delete()
    apps.get_model("omop_core", "HistologicType").objects.all().update(source_name=None, source_url=None)


_new_model_fields = list(_BASE_FIELDS)

_state_ops = [
    migrations.CreateModel(
        name="BreastCancerFirstLineTherapy",
        fields=_new_model_fields,
        options={"db_table": "vocabulary_breast_cancer_first_line_therapy"},
    ),
    migrations.CreateModel(
        name="BreastCancerSecondLineTherapy",
        fields=list(_BASE_FIELDS),
        options={"db_table": "vocabulary_breast_cancer_second_line_therapy"},
    ),
    migrations.CreateModel(
        name="BreastCancerLaterLineTherapy",
        fields=list(_BASE_FIELDS),
        options={"db_table": "vocabulary_breast_cancer_later_line_therapy"},
    ),
]


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0058_seed_receptor_staging_sources"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=sql, reverse_sql=drop)
                for sql, drop in zip(ADD_SQLS, DROP_SQLS)
            ],
            state_operations=_state_ops,
        ),
        migrations.RunPython(seed_forward, seed_reverse),
    ]
