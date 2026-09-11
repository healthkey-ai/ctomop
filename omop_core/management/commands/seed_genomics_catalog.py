from importlib import import_module
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from omop_core.signals import suppress_patient_record_refresh


class Command(BaseCommand):
    help = 'Seed missing approved genomics mappings from the versioned catalog; preserve curator decisions.'

    @transaction.atomic
    def handle(self, **options):
        with suppress_patient_record_refresh(), connection.schema_editor() as editor:
            import_module('omop_core.migrations.0224_seed_genomics_mappings').seed(apps, editor)
        self.stdout.write(self.style.SUCCESS('Genomics catalog mappings seeded. Existing mappings preserved.'))
