from django.db import migrations, models
import django.db.models.deletion

ADD_SQL = """
CREATE TABLE IF NOT EXISTS provenance_record (
    id              SERIAL      PRIMARY KEY,
    source          VARCHAR(50) NOT NULL,
    source_user_id  VARCHAR(255) NOT NULL DEFAULT '',
    target_patient_id VARCHAR(255),
    modification_reason TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_type_id INTEGER     NOT NULL REFERENCES django_content_type(id) ON DELETE CASCADE,
    object_id       BIGINT      NOT NULL
);

CREATE INDEX IF NOT EXISTS prov_content_type_object_idx
    ON provenance_record(content_type_id, object_id);
"""

DROP_SQL = """
DROP INDEX IF EXISTS prov_content_type_object_idx;
DROP TABLE IF EXISTS provenance_record;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('omop_core', '0061_add_organization'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=ADD_SQL, reverse_sql=DROP_SQL),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='ProvenanceRecord',
                    fields=[
                        ('id', models.AutoField(primary_key=True)),
                        ('source', models.CharField(max_length=50, choices=[
                            ('PATIENT_SELF', 'Patient self-entry'),
                            ('ADMIN_CORRECTION', 'Admin on-behalf modification'),
                            ('EHR_SYNC', 'EHR system sync'),
                            ('DOCUMENT_EXTRACTION', 'AI document extraction'),
                        ])),
                        ('source_user_id', models.CharField(max_length=255, blank=True, default='')),
                        ('target_patient_id', models.CharField(max_length=255, null=True, blank=True)),
                        ('modification_reason', models.TextField(null=True, blank=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('content_type', models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            to='contenttypes.contenttype',
                        )),
                        ('object_id', models.PositiveBigIntegerField()),
                    ],
                    options={'db_table': 'provenance_record'},
                ),
                migrations.AddIndex(
                    model_name='provenancerecord',
                    index=models.Index(fields=['content_type', 'object_id'], name='prov_ct_obj_idx'),
                ),
            ],
        )
    ]
