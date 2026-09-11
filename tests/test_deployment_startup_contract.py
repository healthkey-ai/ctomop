from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_production_runs_migrations_before_gunicorn_without_loading_vocabularies():
    script = (ROOT / 'start.sh').read_text()

    migration = 'python manage.py migrate --noinput'
    gunicorn = 'exec gunicorn ctomop.wsgi:application'

    assert 'python manage.py seed_omop_concepts' not in script
    assert 'python manage.py load_athena_vocabularies' not in script
    # Vocabulary preparation is an explicit management operation, not a
    # prerequisite for every web restart (see the start.sh contract in #1124).
    assert 'python manage.py prepare_production_database' not in script
    assert migration in script
    assert script.index(migration) < script.index(gunicorn)


def test_render_web_service_uses_the_tested_startup_script():
    blueprint = (ROOT / 'render.yaml').read_text()

    web_service = blueprint.split('  - type: worker', 1)[0]
    assert 'startCommand: "chmod +x start.sh && ./start.sh"' in web_service
