from django.db import migrations, models

ADD_SQLS = [
    "CREATE TABLE IF NOT EXISTS vocabulary_disease (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT);",
    "CREATE TABLE IF NOT EXISTS vocabulary_cancer_stage (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT);",
    "CREATE TABLE IF NOT EXISTS vocabulary_karnofsky_score (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT, sort_key INTEGER);",
    "CREATE TABLE IF NOT EXISTS vocabulary_ecog_status (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT);",
    "CREATE TABLE IF NOT EXISTS vocabulary_peripheral_neuropathy_grade (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT);",
    "CREATE TABLE IF NOT EXISTS vocabulary_infection_status (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT);",
    "CREATE TABLE IF NOT EXISTS vocabulary_disease_progression (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT);",
    "CREATE TABLE IF NOT EXISTS vocabulary_measurable_disease (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT);",
    "CREATE TABLE IF NOT EXISTS vocabulary_gelf_criteria (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT);",
    "CREATE TABLE IF NOT EXISTS vocabulary_flipi_score (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT);",
    "CREATE TABLE IF NOT EXISTS vocabulary_follicular_lymphoma_grade (id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE, llm_hint TEXT);",
]

DROP_SQLS = [
    "DROP TABLE IF EXISTS vocabulary_disease;",
    "DROP TABLE IF EXISTS vocabulary_cancer_stage;",
    "DROP TABLE IF EXISTS vocabulary_karnofsky_score;",
    "DROP TABLE IF EXISTS vocabulary_ecog_status;",
    "DROP TABLE IF EXISTS vocabulary_peripheral_neuropathy_grade;",
    "DROP TABLE IF EXISTS vocabulary_infection_status;",
    "DROP TABLE IF EXISTS vocabulary_disease_progression;",
    "DROP TABLE IF EXISTS vocabulary_measurable_disease;",
    "DROP TABLE IF EXISTS vocabulary_gelf_criteria;",
    "DROP TABLE IF EXISTS vocabulary_flipi_score;",
    "DROP TABLE IF EXISTS vocabulary_follicular_lymphoma_grade;",
]


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0054_add_preexisting_conditions_jsonfield"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=sql, reverse_sql=drop)
                for sql, drop in zip(ADD_SQLS, DROP_SQLS)
            ],
            state_operations=[
                migrations.CreateModel(
                    name="Disease",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_disease"},
                ),
                migrations.CreateModel(
                    name="CancerStage",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_cancer_stage"},
                ),
                migrations.CreateModel(
                    name="KarnofskyScore",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                        ("sort_key", models.IntegerField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_karnofsky_score", "ordering": ["sort_key"]},
                ),
                migrations.CreateModel(
                    name="EcogStatus",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_ecog_status"},
                ),
                migrations.CreateModel(
                    name="PeripheralNeuropathyGrade",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_peripheral_neuropathy_grade"},
                ),
                migrations.CreateModel(
                    name="InfectionStatus",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_infection_status"},
                ),
                migrations.CreateModel(
                    name="DiseaseProgression",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_disease_progression"},
                ),
                migrations.CreateModel(
                    name="MeasurableDisease",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_measurable_disease"},
                ),
                migrations.CreateModel(
                    name="GelfCriteria",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_gelf_criteria"},
                ),
                migrations.CreateModel(
                    name="FlipIScore",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_flipi_score"},
                ),
                migrations.CreateModel(
                    name="FollicularLymphomaGrade",
                    fields=[
                        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("code", models.TextField(db_index=True, unique=True)),
                        ("title", models.TextField(db_index=True, unique=True)),
                        ("llm_hint", models.TextField(blank=True, null=True)),
                    ],
                    options={"db_table": "vocabulary_follicular_lymphoma_grade"},
                ),
            ],
        )
    ]
