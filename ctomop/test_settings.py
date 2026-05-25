"""Test-only settings for fast, isolated unit tests.

Uses an in-memory SQLite DB so MyChart tests can run without depending on
the dev Postgres or its migration history. Imports everything else from the
main settings module.
"""
from ctomop.settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Some migrations in this project use Postgres-only features (JSONB, IF NOT
# EXISTS in raw SQL, etc.) and can't run on SQLite. The MyChart tests only
# need the auth, contenttypes, oauth2_provider apps plus the four new
# MyChart models + Organization. Other apps are skipped via MIGRATION_MODULES.
MIGRATION_MODULES = {
    'omop_core': None,  # auto-create tables from current model state
    'omop_genomics': None,
    'omop_oncology': None,
    'patient_portal': None,
}

# Speed up password hashing in tests.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
