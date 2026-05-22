from django.db import models
from django.contrib.auth.models import User


class IdentityManager(models.Manager):

    def get_or_create_from_claims(self, claims):
        """Get or create an Identity from TokenClaims."""
        return self.get_or_create(
            issuer=claims.issuer,
            sub=claims.sub,
        )


class Identity(models.Model):
    """OIDC-based identity record: (issuer, sub) tuple.

    Added in Phase A alongside existing User model. Will become
    AUTH_USER_MODEL in Phase C.
    """
    issuer = models.CharField(max_length=255)
    sub = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = IdentityManager()

    class Meta:
        db_table = "identity"
        verbose_name_plural = "identities"
        constraints = [
            models.UniqueConstraint(
                fields=["issuer", "sub"],
                name="uq_identity_issuer_sub",
            ),
        ]

    def __str__(self):
        return f"{self.issuer}|{self.sub}"


class PatientUser(models.Model):
    """Links Django User to OMOP Person for patient portal access"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    identity = models.OneToOneField(
        Identity, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='patient_user',
    )
    person = models.OneToOneField('omop_core.Person', on_delete=models.CASCADE, related_name='portal_user')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'patient_user'

    def __str__(self):
        return f"{self.user.username} - Person {self.person.person_id}"

class PatientConsent(models.Model):
    """Track patient consent for data sharing and clinical trials"""
    patient_user = models.ForeignKey(PatientUser, on_delete=models.CASCADE, related_name='consents')
    consent_type = models.CharField(max_length=50, choices=[
        ('data_sharing', 'Data Sharing'),
        ('clinical_trial', 'Clinical Trial Participation'),
        ('research', 'Research Use'),
    ])
    consent_granted = models.BooleanField(default=False)
    consent_date = models.DateTimeField(auto_now_add=True)
    consent_document = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'patient_consent'
        unique_together = ['patient_user', 'consent_type']
    
    def __str__(self):
        return f"{self.patient_user.user.username} - {self.consent_type}"

class PatientMessage(models.Model):
    """Messages between patients and healthcare providers"""
    patient_user = models.ForeignKey(PatientUser, on_delete=models.CASCADE, related_name='messages')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    sender_is_patient = models.BooleanField(default=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'patient_message'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject} - {self.created_at}"
