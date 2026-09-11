#!/bin/bash
set -e

# Fail the deploy on a misconfigured production environment rather than starting
# with a silent fallback. This is what makes patient_portal.E001/E002/E003 a real
# control: CI runs the same check, but only against CI's own placeholder values,
# which proves nothing about this environment. Runs before migrate so a bad deploy
# stops before touching the database.
#
# Scope, so nobody assumes more coverage than exists: this file is the Render
# service's startCommand (render.yaml, branch main) and is the PRODUCTION path
# only. GCP staging deploys from Dockerfile.gcp, whose CMD is gunicorn directly,
# with migrations in a separate Cloud Run job — start.sh never runs there. So
# staging is NOT gated by this, and production is the first place it can fail a
# deploy. Gating the Cloud Run path needs a change to that job's command.
echo "Running production deploy checks..."
python manage.py check --deploy --fail-level ERROR

: "${ATHENA_VOCABULARY_GDRIVE_URL:?ATHENA_VOCABULARY_GDRIVE_URL must point to the full Athena vocabulary folder before this service can deploy}"
echo "Preparing the production database..."
python manage.py prepare_production_database --gdrive "$ATHENA_VOCABULARY_GDRIVE_URL"

echo "Creating/resetting admin user..."
python manage.py setup_admin

echo "Starting gunicorn..."
exec gunicorn ctomop.wsgi:application
