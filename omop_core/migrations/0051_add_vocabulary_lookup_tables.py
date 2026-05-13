from django.db import migrations, models
import django.db.models.deletion

# ---------------------------------------------------------------------------
# DDL – each table uses IF NOT EXISTS so the migration is idempotent
# ---------------------------------------------------------------------------

TABLES = [
    ("vocabulary_ethnicity",                  "TEXT"),
    ("vocabulary_stem_cell_transplant",       "TEXT"),
    ("vocabulary_histologic_type",            "TEXT"),
    ("vocabulary_estrogen_receptor_status",   "TEXT"),
    ("vocabulary_progesterone_receptor_status", "TEXT"),
    ("vocabulary_her2_status",                "TEXT"),
    ("vocabulary_hr_status",                  "TEXT"),
    ("vocabulary_hrd_status",                 "TEXT"),
    ("vocabulary_mutation_origin",            "TEXT"),
    ("vocabulary_mutation_gene",              "TEXT"),
    ("vocabulary_mutation_interpretation",    "TEXT"),
    ("vocabulary_mutation_code",              "TEXT"),
    ("vocabulary_tumor_stage",                "TEXT"),
    ("vocabulary_nodes_stage",                "TEXT"),
    ("vocabulary_distant_metastasis_stage",   "TEXT"),
    ("vocabulary_staging_modality",           "TEXT"),
    ("vocabulary_language",                   "TEXT"),
    ("vocabulary_language_skill_level",       "TEXT"),
    ("vocabulary_binet_stage",                "TEXT"),
    ("vocabulary_protein_expression",         "TEXT"),
    ("vocabulary_richter_transformation",     "TEXT"),
    ("vocabulary_tumor_burden",               "TEXT"),
    ("vocabulary_morphologic_variant",        "TEXT"),
    ("vocabulary_disease_activity",           "TEXT"),
    ("vocabulary_pre_existing_condition_category", "TEXT"),
]

# Tables that also need a sort_key column
SORT_KEY_TABLES = {
    "vocabulary_histologic_type",
    "vocabulary_tumor_stage",
    "vocabulary_nodes_stage",
    "vocabulary_distant_metastasis_stage",
}


def _base_create(table):
    return f"""
CREATE TABLE IF NOT EXISTS {table} (
    id          SERIAL PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL UNIQUE,
    llm_hint    TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS {table}_code_idx  ON {table} (code);
CREATE INDEX IF NOT EXISTS {table}_title_idx ON {table} (title);
"""


def _base_drop(table):
    return f"DROP TABLE IF EXISTS {table};"


# toxicity_grade uses integer code
TOXICITY_CREATE = """
CREATE TABLE IF NOT EXISTS vocabulary_toxicity_grade (
    id          SERIAL PRIMARY KEY,
    code        INTEGER NOT NULL UNIQUE,
    title       TEXT    NOT NULL UNIQUE,
    llm_hint    TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS vocabulary_toxicity_grade_code_idx  ON vocabulary_toxicity_grade (code);
CREATE INDEX IF NOT EXISTS vocabulary_toxicity_grade_title_idx ON vocabulary_toxicity_grade (title);
"""

TOXICITY_DROP = "DROP TABLE IF EXISTS vocabulary_toxicity_grade;"

# mutation_code has a FK to vocabulary_mutation_gene
MUTATION_CODE_CREATE = """
CREATE TABLE IF NOT EXISTS vocabulary_mutation_code (
    id          SERIAL PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL UNIQUE,
    llm_hint    TEXT,
    gene_id     INTEGER REFERENCES vocabulary_mutation_gene(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS vocabulary_mutation_code_code_idx   ON vocabulary_mutation_code (code);
CREATE INDEX IF NOT EXISTS vocabulary_mutation_code_title_idx  ON vocabulary_mutation_code (title);
CREATE INDEX IF NOT EXISTS vocabulary_mutation_code_gene_idx   ON vocabulary_mutation_code (gene_id);
"""

MUTATION_CODE_DROP = "DROP TABLE IF EXISTS vocabulary_mutation_code;"


def build_up_sql():
    parts = []
    for table, _ in TABLES:
        if table == "vocabulary_mutation_code":
            parts.append(MUTATION_CODE_CREATE)
            continue
        parts.append(_base_create(table))
        if table in SORT_KEY_TABLES:
            parts.append(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS sort_key INTEGER;"
            )
    parts.append(TOXICITY_CREATE)
    return "\n".join(parts)


def build_down_sql():
    # Drop in reverse order; mutation_code first (has FK)
    tables_rev = list(reversed([t for t, _ in TABLES]))
    parts = [TOXICITY_DROP]
    for table in tables_rev:
        parts.append(_base_drop(table))
    return "\n".join(parts)


UP_SQL = build_up_sql()
DOWN_SQL = build_down_sql()


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0050_alter_patientdocument_id"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=UP_SQL, reverse_sql=DOWN_SQL),
            ],
            state_operations=[
                # --- Simple text-code lookup tables ---
                migrations.CreateModel(
                    name="Ethnicity",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_ethnicity"},
                ),
                migrations.CreateModel(
                    name="StemCellTransplant",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_stem_cell_transplant"},
                ),
                migrations.CreateModel(
                    name="HistologicType",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                        ("sort_key", models.IntegerField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_histologic_type", "ordering": ["sort_key"]},
                ),
                migrations.CreateModel(
                    name="EstrogenReceptorStatus",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_estrogen_receptor_status"},
                ),
                migrations.CreateModel(
                    name="ProgesteroneReceptorStatus",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_progesterone_receptor_status"},
                ),
                migrations.CreateModel(
                    name="Her2Status",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_her2_status"},
                ),
                migrations.CreateModel(
                    name="HrStatus",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_hr_status"},
                ),
                migrations.CreateModel(
                    name="HrdStatus",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_hrd_status"},
                ),
                migrations.CreateModel(
                    name="MutationOrigin",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_mutation_origin"},
                ),
                migrations.CreateModel(
                    name="MutationGene",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_mutation_gene"},
                ),
                migrations.CreateModel(
                    name="MutationInterpretation",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_mutation_interpretation"},
                ),
                migrations.CreateModel(
                    name="MutationCode",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                        (
                            "gene",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="mutation_codes",
                                to="omop_core.mutationgene",
                            ),
                        ),
                    ],
                    options={"db_table": "vocabulary_mutation_code"},
                ),
                migrations.CreateModel(
                    name="TumorStage",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                        ("sort_key", models.IntegerField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_tumor_stage", "ordering": ["sort_key"]},
                ),
                migrations.CreateModel(
                    name="NodesStage",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                        ("sort_key", models.IntegerField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_nodes_stage", "ordering": ["sort_key"]},
                ),
                migrations.CreateModel(
                    name="DistantMetastasisStage",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                        ("sort_key", models.IntegerField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_distant_metastasis_stage", "ordering": ["sort_key"]},
                ),
                migrations.CreateModel(
                    name="StagingModality",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_staging_modality"},
                ),
                migrations.CreateModel(
                    name="ToxicityGrade",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.IntegerField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_toxicity_grade", "ordering": ["code"]},
                ),
                migrations.CreateModel(
                    name="Language",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_language"},
                ),
                migrations.CreateModel(
                    name="LanguageSkillLevel",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_language_skill_level"},
                ),
                migrations.CreateModel(
                    name="BinetStage",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_binet_stage"},
                ),
                migrations.CreateModel(
                    name="ProteinExpression",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_protein_expression"},
                ),
                migrations.CreateModel(
                    name="RichterTransformation",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_richter_transformation"},
                ),
                migrations.CreateModel(
                    name="TumorBurden",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_tumor_burden"},
                ),
                migrations.CreateModel(
                    name="MorphologicVariant",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_morphologic_variant"},
                ),
                migrations.CreateModel(
                    name="DiseaseActivity",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_disease_activity"},
                ),
                migrations.CreateModel(
                    name="PreExistingConditionCategory",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_pre_existing_condition_category"},
                ),
            ],
        )
    ]
