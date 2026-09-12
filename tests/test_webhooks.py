import hashlib
import hmac
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.db import close_old_connections, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from omop_core.models import GroupAccess, Organization, PatientDocument, PatientRecord, Person
from patient_portal.models import Identity, InboundWebhookEvent, WebhookDelivery, WebhookSubscription
from patient_portal.tasks import deliver_webhook, dispatch_pending_webhooks
from patient_portal.webhooks import (
    compute_hmac_signature, encode_payload, enqueue_delivery, publish_event,
    resolve_webhook_url, send_webhook,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(settings):
    settings.CELERY_BROKER_URL = ''
    org = Organization.objects.create(name='Webhook tenant', slug='webhook-tenant')
    other = Organization.objects.create(name='Other tenant', slug='webhook-other')
    person = Person.objects.create(person_id=420001)
    PatientRecord.objects.create(person=person, organization=org)
    user = Identity.objects.create_user(email='webhook-admin@example.org')
    GroupAccess.objects.create(identity=user, org=org, role='org_admin')
    settings.WEBHOOK_INBOUND_SOURCES = {
        'lab-system': {'secret': 'test-source-secret', 'organization': org.slug},
    }
    subscription = WebhookSubscription.objects.create(
        organization=org, url='https://subscriber.example/events',
        event_types=['patient.changed', 'lab.updated', 'document.received', 'foundation.synced'],
    )
    return org, other, person, user, subscription


def inbound(payload=None, signature=None, source='lab-system', **headers):
    payload = payload or {'id': 'event-1', 'type': 'lab.updated', 'data': {'person_id': 420001}}
    body = payload if isinstance(payload, bytes) else encode_payload(payload)
    return APIClient().post(
        '/api/webhooks/inbound/', body, content_type='application/json',
        HTTP_X_HEALTHKEY_SOURCE=source,
        HTTP_X_HEALTHKEY_SIGNATURE=signature if signature is not None else compute_hmac_signature(body, 'test-source-secret'),
        **headers,
    )


def test_hmac_matches_standard():
    payload = b'{"exact": "bytes"}\n'
    expected = 'sha256=' + hmac.new(b'secret', payload, hashlib.sha256).hexdigest()
    assert compute_hmac_signature(payload, 'secret') == expected
    assert compute_hmac_signature(payload.rstrip(), 'secret') != expected


@pytest.mark.parametrize('signature', ['', 'invalid', 'sha256=' + '0' * 64, 'é'])
def test_inbound_rejects_bad_signature(setup, signature):
    assert inbound(signature=signature).status_code == 401
    assert not InboundWebhookEvent.objects.exists()


def test_unknown_source_cannot_select_org(setup):
    assert inbound(source='other').status_code == 401
    assert not WebhookDelivery.objects.exists()


@pytest.mark.parametrize('event_type', ['lab.updated', 'document.received', 'foundation.synced'])
def test_inbound_dispatch_and_deduplication(setup, event_type):
    org, other, person, user, subscription = setup
    WebhookSubscription.objects.create(organization=other, url=subscription.url, event_types=[event_type])
    payload = {'id': 'event-1', 'type': event_type, 'data': {'person_id': person.pk, 'resource_id': 'external-42'}}
    assert inbound(payload, HTTP_IDEMPOTENCY_KEY='event-1').status_code == 202
    assert inbound(payload).data['duplicate'] is True
    assert InboundWebhookEvent.objects.get().processed_at is not None
    delivery = WebhookDelivery.objects.get()
    assert delivery.subscription_id == subscription.pk
    assert delivery.payload['type'] == event_type
    assert delivery.payload['data']['resource_id'] == 'external-42'


def test_id_reuse_with_changed_payload_conflicts(setup):
    assert inbound().status_code == 202
    assert inbound({'id': 'event-1', 'type': 'document.received', 'data': {'person_id': 420001}}).status_code == 409
    assert WebhookDelivery.objects.count() == 1


@pytest.mark.parametrize('payload', [
    b'not JSON', b'null', b'[]', b'{}',
    {'id': 'x', 'type': 'unsupported', 'data': {'person_id': 420001}},
    {'id': 'x', 'type': 'lab.updated', 'data': {'person_id': 'invalid'}},
    {'id': 'x', 'type': 'lab.updated', 'data': {}},
])
def test_signed_invalid_payload_rejected(setup, payload):
    assert inbound(payload).status_code == 400
    assert not InboundWebhookEvent.objects.exists()


def test_source_cannot_notify_another_tenant(setup):
    org, other, person, user, subscription = setup
    PatientRecord.objects.filter(person=person).update(organization=other)
    assert inbound().status_code == 400
    assert not WebhookDelivery.objects.exists()


def test_unsigned_idempotency_key_must_match_signed_id(setup):
    assert inbound(HTTP_IDEMPOTENCY_KEY='different').status_code == 400


def test_subscription_management_and_secret_visibility(setup):
    org, other, person, user, subscription = setup
    client = APIClient()
    client.force_authenticate(user)
    with patch('patient_portal.api.webhook_views.resolve_webhook_url'):
        response = client.post('/api/webhooks/subscriptions/', {
            'organization': org.pk, 'url': subscription.url, 'event_types': ['lab.updated'],
        }, format='json')
        assert response.status_code == 201
        assert len(response.data['secret']) >= 32
        assert client.post('/api/webhooks/subscriptions/', {
            'organization': other.pk, 'url': subscription.url, 'event_types': ['lab.updated'],
        }, format='json').status_code == 400
    assert 'secret' not in client.get(f'/api/webhooks/subscriptions/{subscription.pk}/').data
    assert subscription.secret not in client.get('/api/webhooks/subscriptions/').content.decode()
    alien = WebhookSubscription.objects.create(organization=other, url=subscription.url, event_types=['lab.updated'])
    assert client.get(f'/api/webhooks/subscriptions/{alien.pk}/deliveries/').status_code == 404
    assert client.patch(f'/api/webhooks/subscriptions/{alien.pk}/', {'active': False}, format='json').status_code == 404
    assert client.patch(f'/api/webhooks/subscriptions/{subscription.pk}/', {'organization': other.pk}, format='json').status_code == 400
    assert client.patch(f'/api/webhooks/subscriptions/{subscription.pk}/', {'active': False}, format='json').status_code == 200


def test_patient_and_expired_admin_cannot_manage_subscriptions(setup):
    org, other, person, user, subscription = setup
    client = APIClient()
    assert client.get('/api/webhooks/subscriptions/').status_code in (401, 403)
    client.force_authenticate(user)
    GroupAccess.objects.filter(identity=user).update(role='patient')
    assert client.get('/api/webhooks/subscriptions/').status_code == 403
    GroupAccess.objects.filter(identity=user).update(role='org_admin', expires_at=timezone.now() - timedelta(seconds=1))
    assert client.get('/api/webhooks/subscriptions/').status_code == 403


def test_rollback_discards_event_and_queue_dispatch(setup, django_capture_on_commit_callbacks):
    with patch('patient_portal.webhooks.enqueue_delivery') as enqueue:
        with django_capture_on_commit_callbacks(execute=True):
            with pytest.raises(RuntimeError), transaction.atomic():
                publish_event(setup[0].pk, 'patient.changed', {'person_id': setup[2].pk})
                raise RuntimeError('rollback')
        enqueue.assert_not_called()
    assert not WebhookDelivery.objects.exists()


def test_model_changes_queue_only_after_commit(setup, django_capture_on_commit_callbacks):
    with patch('patient_portal.webhooks.enqueue_delivery') as enqueue:
        with django_capture_on_commit_callbacks(execute=True):
            PatientDocument.objects.create(person=setup[2], doc_type='OTHER')
            enqueue.assert_not_called()
            assert WebhookDelivery.objects.get().payload['type'] == 'document.received'
        enqueue.assert_called_once()


def test_lab_sync_bulk_write_emits_one_notification(setup, django_capture_on_commit_callbacks):
    org, other, person, user, subscription = setup
    user.is_staff = True
    user.save(update_fields=['is_staff'])
    client = APIClient()
    client.force_authenticate(user)
    with patch('patient_portal.webhooks.enqueue_delivery') as enqueue:
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post('/api/lab-results/sync/', {
                'person_id': person.pk,
                'measurements': [{'test_name': 'Webhook lab', 'value': '42', 'measured_at': '2026-09-12'}],
            }, format='json')
            assert response.status_code == 201, response.data
            enqueue.assert_not_called()
        enqueue.assert_called_once()
    delivery = WebhookDelivery.objects.get()
    assert delivery.payload['type'] == 'lab.updated'
    assert delivery.payload['data']['count'] == 1


@pytest.mark.parametrize('operation', ['update', 'delete'])
def test_bulk_changes_notify_even_when_refresh_is_skipped(setup, operation):
    user = setup[3]
    user.is_staff = True
    user.save(update_fields=['is_staff'])
    client = APIClient()
    client.force_authenticate(user)
    response = client.post('/api/lab-results/sync/', {
        'person_id': setup[2].pk,
        'measurements': [{'test_name': 'Webhook bulk', 'value': '42', 'measured_at': '2026-09-12'}],
    }, format='json')
    assert response.status_code == 201, response.data
    measurement_id = response.data['measurement_ids'][0]
    WebhookDelivery.objects.all().delete()
    body = ({'ids': [measurement_id]} if operation == 'delete' else
            [{'measurement_id': measurement_id, 'value_as_number': 43}])
    send = client.post if operation == 'delete' else client.patch
    response = send(f'/api/v1/measurements/bulk_{operation}/?skip_refresh=true', body, format='json')
    assert response.status_code == 200, response.data
    delivery = WebhookDelivery.objects.get()
    assert delivery.payload['type'] == ('patient.changed' if operation == 'delete' else 'lab.updated')
    assert delivery.payload['data']['count'] == 1


@pytest.fixture
def delivery(setup):
    return WebhookDelivery.objects.create(subscription=setup[4], payload={'id': 'event', 'type': 'lab.updated', 'data': {}})


def test_successful_delivery_and_duplicate_task(delivery):
    with patch('patient_portal.tasks.send_webhook', return_value=204) as send:
        deliver_webhook(str(delivery.pk))
        deliver_webhook(str(delivery.pk))
        send.assert_called_once()
    delivery.refresh_from_db()
    assert delivery.status == 'delivered'
    assert delivery.attempts == 1
    assert delivery.delivered_at is not None


@pytest.mark.parametrize('response_status', [301, 400, 401, 429, 500, 503])
def test_retry_backoff_and_five_attempt_limit(delivery, response_status, django_capture_on_commit_callbacks):
    with patch('patient_portal.tasks.send_webhook', return_value=response_status) as send:
        with patch('patient_portal.tasks.enqueue_delivery') as enqueue:
            for attempt in range(1, 6):
                with django_capture_on_commit_callbacks(execute=True):
                    deliver_webhook(str(delivery.pk))
                delivery.refresh_from_db()
                assert delivery.attempts == attempt
                assert delivery.response_status == response_status
                if attempt < 5:
                    assert delivery.status == 'retry'
                    assert enqueue.call_args.kwargs['countdown'] == 30 * 2 ** (attempt - 1)
                    deliver_webhook(str(delivery.pk))
                    assert send.call_count == attempt
                    WebhookDelivery.objects.filter(pk=delivery.pk).update(next_attempt_at=timezone.now())
            assert delivery.status == 'dead_letter'
            deliver_webhook(str(delivery.pk))
            assert send.call_count == 5
            assert enqueue.call_count == 4


def test_network_errors_are_redacted_and_retried(delivery):
    with patch('patient_portal.tasks.send_webhook', side_effect=OSError('secret in a URL')):
        deliver_webhook(str(delivery.pk))
    delivery.refresh_from_db()
    assert delivery.status == 'retry'
    assert delivery.error == 'connection_error'


def test_disabled_subscription_is_not_delivered(delivery):
    WebhookSubscription.objects.filter(pk=delivery.subscription_id).update(active=False)
    with patch('patient_portal.tasks.send_webhook') as send:
        deliver_webhook(str(delivery.pk))
        send.assert_not_called()
    delivery.refresh_from_db()
    assert delivery.status == 'cancelled'
    assert delivery.attempts == 0


def test_broker_failure_retains_outbox_for_sweep(delivery, settings):
    settings.CELERY_BROKER_URL = 'redis://unavailable'
    with patch('patient_portal.tasks.deliver_webhook.apply_async', side_effect=OSError):
        enqueue_delivery(delivery.pk)
    delivery.refresh_from_db()
    assert delivery.status == 'pending'
    with patch('patient_portal.tasks.enqueue_delivery') as enqueue:
        dispatch_pending_webhooks()
        enqueue.assert_called_once_with(delivery.pk)


def test_lost_worker_lease_recovers_with_attempt_limit(delivery):
    WebhookDelivery.objects.filter(pk=delivery.pk).update(status='sending', attempts=5)
    with patch('patient_portal.tasks.send_webhook') as send:
        deliver_webhook(str(delivery.pk))
        send.assert_not_called()
    delivery.refresh_from_db()
    assert delivery.status == 'dead_letter'


@pytest.mark.parametrize('url', [
    'http://example.com/', 'https://user:password@example.com/',
    'https://example.com:8080/', 'https://example.com/#fragment',
])
def test_unsafe_url_schemes_and_credentials(url):
    with pytest.raises(ValueError):
        resolve_webhook_url(url)


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', 'fd00::1', '::ffff:127.0.0.1'])
def test_private_destinations_rejected(address):
    with patch('socket.getaddrinfo', return_value=[(socket.AF_INET, 1, 6, '', (address, 443))]):
        with pytest.raises(ValueError):
            resolve_webhook_url('https://subscriber.example/')


def test_transport_pins_ip_verifies_tls_signs_bytes_and_disables_redirects():
    response = Mock(status=302)
    with patch('socket.getaddrinfo', return_value=[(socket.AF_INET, 1, 6, '', ('8.8.8.8', 443))]):
        with patch('patient_portal.webhooks.urllib3.HTTPSConnectionPool') as pool:
            pool.return_value.urlopen.return_value = response
            assert send_webhook('https://subscriber.example/path?a=1', {'id': 'x'}, 'secret', 'delivery') == 302
    assert pool.call_args.args == ('8.8.8.8',)
    assert pool.call_args.kwargs['server_hostname'] == 'subscriber.example'
    assert pool.call_args.kwargs['assert_hostname'] == 'subscriber.example'
    assert pool.call_args.kwargs['cert_reqs'] == 'CERT_REQUIRED'
    args, kwargs = pool.return_value.urlopen.call_args
    assert args == ('POST', '/path?a=1')
    assert kwargs['redirect'] is False
    assert kwargs['retries'] is False
    assert kwargs['preload_content'] is False
    assert kwargs['headers']['X-HealthKey-Signature'] == compute_hmac_signature(kwargs['body'], 'secret')
    response.close.assert_called_once()


@pytest.mark.parametrize('url,address,hostname,host_header', [
    ('https://[2606:4700:4700::1111]/', '2606:4700:4700::1111', '2606:4700:4700::1111', '[2606:4700:4700::1111]'),
    ('https://bücher.example/', '8.8.8.8', 'xn--bcher-kva.example', 'xn--bcher-kva.example'),
])
def test_transport_normalizes_ipv6_and_idna_hosts(url, address, hostname, host_header):
    with patch('socket.getaddrinfo', return_value=[(socket.AF_INET6, 1, 6, '', (address, 443))]) as dns:
        with patch('patient_portal.webhooks.urllib3.HTTPSConnectionPool') as pool:
            pool.return_value.urlopen.return_value = Mock(status=200)
            send_webhook(url, {'id': 'event'}, 'secret', 'delivery')
    assert dns.call_args.args[0] == hostname
    assert pool.call_args.kwargs['server_hostname'] == hostname
    assert pool.return_value.urlopen.call_args.kwargs['headers']['Host'] == host_header


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_inbound_events(setup):
    def receive():
        close_old_connections()
        try:
            return inbound().status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: receive(), range(2)))
    assert sorted(results) == [200, 202]
    assert InboundWebhookEvent.objects.count() == 1
    assert WebhookDelivery.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_delivery_tasks_send_once(delivery):
    def run():
        close_old_connections()
        try:
            deliver_webhook(str(delivery.pk))
        finally:
            close_old_connections()

    with patch('patient_portal.tasks.send_webhook', return_value=200) as send:
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(lambda _: run(), range(2)))
        send.assert_called_once()
    delivery.refresh_from_db()
    assert delivery.attempts == 1
