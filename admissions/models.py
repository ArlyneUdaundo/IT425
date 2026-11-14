from django.conf import settings
from django.db import models

from .validators import admission_document_upload_to, validate_admission_document


class AdmissionApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    application_number = models.CharField(max_length=24, unique=True)
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80)
    suffix = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField()
    address = models.TextField()
    preferred_course = models.ForeignKey(
        "students.Course",
        on_delete=models.PROTECT,
        related_name="admission_applications",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.SUBMITTED
    )
    review_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_generated = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_admissions",
        null=True,
        blank=True,
    )
    student = models.OneToOneField(
        "students.Student",
        on_delete=models.SET_NULL,
        related_name="admission_application",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.application_number} — {self.last_name}, {self.first_name}"


class AdmissionDocument(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    application = models.ForeignKey(
        AdmissionApplication, on_delete=models.CASCADE, related_name="documents"
    )
    requirement_name = models.CharField(max_length=120)
    file = models.FileField(
        upload_to=admission_document_upload_to,
        validators=[validate_admission_document],
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.RECEIVED
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=240, blank=True)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["requirement_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "requirement_name"],
                name="unique_admission_requirement",
            )
        ]

    def __str__(self):
        return f"{self.application.application_number}: {self.requirement_name}"
