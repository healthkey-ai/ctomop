from django.test import SimpleTestCase, override_settings

from patient_portal.checks import production_key_separation_check


class ProductionKeySeparationCheckTest(SimpleTestCase):
    def _check(self, **settings):
        with override_settings(**settings):
            return production_key_separation_check(None)

    def test_development_allows_fallback_keys(self):
        self.assertEqual(self._check(DEBUG=True, SECRET_KEY='django-secret'), [])

    def test_production_requires_both_dedicated_keys(self):
        errors = self._check(DEBUG=False, SECRET_KEY='django-secret')

        self.assertEqual({error.id for error in errors}, {
            'patient_portal.E001', 'patient_portal.E002',
        })

    def test_production_rejects_secret_key_reuse(self):
        errors = self._check(
            DEBUG=False,
            SECRET_KEY='django-secret',
            AUDIT_HMAC_KEY='django-secret',
            EXPORT_SIGNING_KEY='export-secret',
        )

        self.assertEqual([error.id for error in errors], ['patient_portal.E001'])

    def test_production_rejects_shared_audit_and_export_key(self):
        errors = self._check(
            DEBUG=False,
            SECRET_KEY='django-secret',
            AUDIT_HMAC_KEY='shared-secret',
            EXPORT_SIGNING_KEY='shared-secret',
        )

        self.assertEqual([error.id for error in errors], ['patient_portal.E003'])

    def test_production_accepts_separate_dedicated_keys(self):
        errors = self._check(
            DEBUG=False,
            SECRET_KEY='django-secret',
            AUDIT_HMAC_KEY='audit-secret',
            EXPORT_SIGNING_KEY='export-secret',
        )

        self.assertEqual(errors, [])


class SecurityPostureCheckTest(SimpleTestCase):
    def test_deployed_debug_still_requires_separate_keys(self):
        with override_settings(DEBUG=True, IS_DEPLOYED=True, AUDIT_HMAC_KEY='', EXPORT_SIGNING_KEY=''):
            self.assertEqual(
                {error.id for error in production_key_separation_check(None)},
                {'patient_portal.E001', 'patient_portal.E002'},
            )

    def test_posture_is_deploy_only_and_never_reports_secrets(self):
        import json
        from django.core.checks import run_checks, Tags
        with override_settings(SECRET_KEY='never-print-this', PHR_AUDIENCE='private-audience'):
            ordinary = run_checks(tags=[Tags.security])
            deployed = run_checks(tags=[Tags.security], include_deployment_checks=True)
        self.assertNotIn('patient_portal.I001', {item.id for item in ordinary})
        report = next(item for item in deployed if item.id == 'patient_portal.I001')
        self.assertNotIn('never-print-this', report.msg)
        self.assertNotIn('private-audience', report.msg)
        self.assertTrue(json.loads(report.msg.split(': ', 1)[1])['PHR_AUDIENCE_CONFIGURED'])

    def test_explicit_overrides_are_reported_as_warnings(self):
        from patient_portal.checks import security_posture_check
        with override_settings(
            ALLOWED_HOSTS=['*'], CORS_ALLOW_ALL_ORIGINS=True,
            FIREBASE_SKIP_REVOCATION_CHECK=True,
            REST_FRAMEWORK={'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.BasicAuthentication']},
            OAUTH2_PROVIDER={'ALLOWED_REDIRECT_URI_SCHEMES': ['https', 'http']},
        ):
            messages = security_posture_check(None)
        self.assertEqual(sum(item.id == 'patient_portal.W006' for item in messages), 5)

    def test_deployed_debug_still_checks_shared_throttle_cache(self):
        from patient_portal.checks import throttle_cache_is_shared_check
        with override_settings(DEBUG=True, IS_DEPLOYED=True, CACHES={
            'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
        }):
            self.assertEqual([item.id for item in throttle_cache_is_shared_check(None)], ['patient_portal.W005'])
