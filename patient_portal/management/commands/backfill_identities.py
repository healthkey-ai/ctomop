"""Backfill Identity records for existing PatientUser rows.

Phase A migration: creates an Identity row for each PatientUser whose
linked User has a Firebase-provisioned account (identified by email lookup
in existing partner auth flow).
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from patient_portal.models import Identity, PatientUser

FIREBASE_ISS_PREFIX = "https://securetoken.google.com/"


class Command(BaseCommand):
    help = "Create Identity records for existing PatientUser rows"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be done without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        firebase_project = getattr(settings, "FIREBASE_PROJECT_ID", None)
        if not firebase_project:
            self.stderr.write(
                "FIREBASE_PROJECT_ID not set in settings. "
                "Cannot determine issuer for backfill."
            )
            return

        issuer = f"{FIREBASE_ISS_PREFIX}{firebase_project}"

        patient_users = PatientUser.objects.filter(
            identity__isnull=True,
        ).select_related("user")

        total = patient_users.count()
        self.stdout.write(f"Found {total} PatientUser rows without identity (issuer={issuer})")

        if dry_run:
            self.stdout.write("Dry run — no changes made.")
            return

        created = 0
        linked = 0
        skipped = 0

        for pu in patient_users.iterator():
            username = pu.user.username
            if not username or "@" in username:
                skipped += 1
                continue

            identity, was_created = Identity.objects.get_or_create(
                issuer=issuer,
                sub=username,
            )
            pu.identity = identity
            pu.save(update_fields=["identity"])

            if was_created:
                created += 1
            else:
                linked += 1

        self.stdout.write(
            f"Done. Created {created} identities, "
            f"linked {linked} existing, skipped {skipped}."
        )
