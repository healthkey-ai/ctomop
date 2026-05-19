import json
from django.core.management.base import BaseCommand
from omop_core.models import Person
from omop_core.services.lot_inference_service import infer_lot_for_person


class Command(BaseCommand):
    help = 'Infer lines of therapy from DrugExposure + ProcedureOccurrence rows and persist as Episode records.'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--person-id', type=int, dest='person_id', help='Run for a single person_id')
        group.add_argument('--all', action='store_true', help='Run for all persons with DrugExposure but no Episodes')
        parser.add_argument('--force', action='store_true', help='Re-run even if Episodes already exist')
        parser.add_argument('--dry-run', action='store_true', help='Print inferred LOTs without writing to DB')

    def handle(self, *args, **options):
        person_id = options.get('person_id')
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)

        if person_id:
            persons = Person.objects.filter(person_id=person_id)
        else:
            persons = Person.objects.filter(drugexposure__isnull=False).distinct()

        verbosity = options.get('verbosity', 1)
        for person in persons:
            lots = infer_lot_for_person(person, force=force, dry_run=dry_run)
            if lots and verbosity >= 1:
                self.stdout.write(json.dumps({
                    'person_id': person.person_id,
                    'dry_run': dry_run,
                    'lots': [
                        {
                            'lot_number': lot.lot_number,
                            'regimen': lot.regimen_name,
                            'phase': lot.phase_label,
                            'source_value': lot.source_value,
                            'start': str(lot.start),
                            'end': str(lot.end) if lot.end else None,
                            'drug_exposures': len(lot.exposure_ids),
                            'procedures': len(lot.procedure_ids),
                        }
                        for lot in lots
                    ],
                }))
